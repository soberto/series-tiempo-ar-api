#! coding: utf-8
import re
from abc import abstractmethod

from datetime import datetime
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient

from elastic_spike.apps.api.query import Query, CollapseQuery


class QueryPipeline:
    """Pipeline del proceso de queries de la serie de tiempo. Ejecuta
    varias operaciones o comandos sobre un objeto query, usando los
    parámetros pasados por el request"""
    def __init__(self, request_args):
        """
        Args:
            request_args (dict): dict con los parámetros del GET
                request
        """
        self.args = request_args
        self.result = {}
        self.elastic = Elasticsearch()
        self.commands = self.init_commands()
        self.run()

    def run(self):
        query = Query()
        for cmd in self.commands:
            cmd_instance = cmd()
            query = cmd_instance.run(query, self.args)
            if cmd_instance.errors:
                self.result['errors'] = cmd_instance.errors.copy()
                return

        self.result['data'] = query.data

    @staticmethod
    def init_commands():
        """Lista con las operaciones a ejecutar"""
        return [
            NameAndRepMode,
            DateFilter,
            Pagination,
            Collapse,
            Execute
        ]


class BaseOperation:
    def __init__(self):
        self.errors = []

    @abstractmethod
    def run(self, query, args):
        """Ejecuta la operación del pipeline sobre el parámetro series

        Args:
            query (Query)
            args (dict): parámetros del request
        Returns:
            Query: nuevo objeto query, el original con la operación
                pertinente aplicada
        """
        raise NotImplementedError

    def append_error(self, msg):
        self.errors.append({
            'error': msg
        })


class Pagination(BaseOperation):
    """Agrega paginación de resultados a una búsqueda"""

    def run(self, query, args):
        start = args.get('start', settings.API_DEFAULT_VALUES['start'])
        limit = args.get('limit', settings.API_DEFAULT_VALUES['limit'])
        self.validate_arg(start)
        self.validate_arg(limit, min_value=1)
        if self.errors:
            raise ValueError

        start = int(start)
        limit = start + int(limit)
        query.add_pagination(start, limit)
        return query

    def validate_arg(self, arg, min_value=0):
        try:
            parsed_arg = int(arg)
        except ValueError:
            parsed_arg = None

        if parsed_arg is None or parsed_arg < min_value:
            self.append_error("Parámetro 'limit' inválido: {}".format(arg))


class DateFilter(BaseOperation):
    def __init__(self):
        super().__init__()
        self.start = None
        self.end = None

    def run(self, query, args):
        self.start = args.get('start_date')
        self.end = args.get('end_date')

        self.validate_start_end_dates()
        if self.errors:
            raise ValueError

        query.add_filter(self.start, self.end)
        return query

    def validate_start_end_dates(self):
        """Valida el intervalo de fechas (start, end). Actualiza la
        lista de errores de ser necesario.
        """

        parsed_start, parsed_end = None, None
        if self.start:
            try:
                parsed_start = self.validate_date(self.start)
            except ValueError:
                pass

        if self.end:
            try:
                parsed_end = self.validate_date(self.end)
            except ValueError:
                pass

        if parsed_start and parsed_end:
            if parsed_start > parsed_end:
                error = "Filtro por rango temporal inválido (start > end)"
                self.append_error(error)

    def validate_date(self, date):
        full_date = r'\d{4}-\d{2}-\d{2}'
        year_and_month = r'\d{4}-\d{2}'
        year_only = r'\d{4}'

        if re.fullmatch(full_date, date):
            parsed_date = datetime.strptime(date, '%Y-%m-%d')
        elif re.fullmatch(year_and_month, date):
            parsed_date = datetime.strptime(date, "%Y-%m")
        elif re.fullmatch(year_only, date):
            parsed_date = datetime.strptime(date, "%Y")
        else:
            error = 'Formato de rango temporal inválido: {}'.format(date)
            self.append_error(error)
            raise ValueError
        return parsed_date


class NameAndRepMode(BaseOperation):
    """Asigna el doc_type a la búsqueda, el identificador de cada
    serie de tiempo individual, y rep_mode, el modo de representación,
    a base de el parseo el parámetro 'ids', que contiene datos de
    varias series a la vez
    """

    def __init__(self):
        super().__init__()
        self.elastic = Elasticsearch()
        self.ids = None

    def run(self, query, args):
        self.ids = args.get('ids')
        if not self.ids:
            self.append_error('No se especificó una serie de tiempo.')
            return

        name, rep_mode = self.parse_series(self.ids, args)
        self.validate(name, rep_mode)

        query.add_series(name, rep_mode)
        return query

    def validate(self, doc_type, rep_mode):
        indices = IndicesClient(client=self.elastic)
        if not indices.exists_type(index="indicators",
                                   doc_type=doc_type):
            self.append_error('Serie inválida: {}'.format(self.ids))

        if rep_mode not in settings.REP_MODES:
            error = "Modo de representación inválido: {}".format(rep_mode)
            self.append_error(error)

    def parse_series(self, serie, args):
        """Parsea una serie invididual. Actualiza la lista de errores
            en caso de encontrar alguno
        Args:
            serie (str): string con formato de tipo 'id:rep_mode'
            args (dict): argumentos de la query

        Returns:
            nombre y rep_mode parseados
        """

        # rep_mode 'default', para todas las series, overrideado
        # si la serie individual especifica alguno
        rep_mode = args.get('representation-mode',
                            settings.API_DEFAULT_VALUES['rep_mode'])
        colon_index = serie.find(':')
        if colon_index < 0:
            name = serie
        else:
            try:
                name, rep_mode = serie.split(':')
            except ValueError:
                self.append_error("Formato de series a seleccionar inválido")
                return
        return name, rep_mode


class Collapse(BaseOperation):
    """Maneja las distintas agregaciones (suma, promedio)"""
    def run(self, query, args):
        collapse = args.get('collapse')
        if not collapse:
            return query

        agg = args.get('collapse_aggregation',
                       settings.API_DEFAULT_VALUES['collapse_aggregation'])
        global_rep_mode = args.get('representation_mode',
                                   settings.API_DEFAULT_VALUES['rep_mode'])
        for serie in query.series:
            search = serie['search']
            rep_mode = serie.get('rep_mode', global_rep_mode)
            search = search[:0]
            search.aggs.bucket('agg',
                               'date_histogram',
                               field='timestamp',
                               interval=collapse).metric('agg',
                                                         agg,
                                                         field=rep_mode)
            serie['search'] = search

        return CollapseQuery(query)


class Execute(BaseOperation):
    def run(self, query, args):
        query.run()
        return query