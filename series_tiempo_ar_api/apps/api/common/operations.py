#! coding: utf-8

"""Operaciones de cálculos de variaciones absolutas y porcentuales anuales"""

from calendar import monthrange

import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from django.conf import settings

from series_tiempo_ar_api.apps.api.common import constants
from series_tiempo_ar_api.apps.api.helpers import freq_pandas_to_index_offset, \
    freq_pandas_to_interval


def get_value(df, col, index):
    """Devuelve el valor del df[col][index] o 0 si no es válido.
    Evita Cargar Infinity y NaN en Elasticsearch
    """
    series = df[col]
    if index not in series:
        return 0

    value = series[index]
    return value if np.isfinite(value) else 0


def year_ago_column(col, freq, operation):
    """Aplica operación entre los datos de una columna y su valor
    un año antes. Devuelve una nueva serie de pandas.
    """
    array = []
    offset = freq_pandas_to_index_offset(freq.freqstr) or 0
    if offset:
        values = col.values
        array = operation(values[offset:], values[:-offset])
    else:
        for idx, val in col.iteritems():
            value = get_value_a_year_ago(idx, col, validate=True)
            if value != 0:
                array.append(operation(val, value))
            else:
                array.append(None)

    return pd.Series(array, index=col.index[offset:])


def get_value_a_year_ago(idx, col, validate=False):
    """Devuelve el valor de la serie determinada por df[col] un
    año antes del índice de tiempo 'idx'. Hace validación de si
    existe el índice o no según 'validate' (operación costosa)
    """

    value = 0
    year_ago_idx = idx.date() - relativedelta(years=1)
    if not validate:
        if year_ago_idx not in col.index:
            return 0

        value = col[year_ago_idx]
    else:
        if year_ago_idx in col:
            value = col[year_ago_idx]

    return value


def change_a_year_ago(col, freq):
    def change(x, y):
        return x - y
    return year_ago_column(col, freq, change)


def pct_change_a_year_ago(col, freq):
    def _pct_change(x, y):
        if isinstance(y, int) and y == 0:
            return 0
        return (x - y) / y

    return year_ago_column(col, freq, _pct_change)


def process_column(col, index):
    """Procesa una columna de la serie, calculando los valores de todas las
    transformaciones posibles para todos los intervalos de tiempo. Devuelve
    la lista de acciones (dicts) a indexar en Elasticsearch
    """

    # Filtro de valores nulos iniciales/finales
    col = col[col.first_valid_index():col.last_valid_index()]

    orig_freq = col.index.freq
    series_id = col.name

    actions = []
    # Lista de intervalos temporales de pandas EN ORDEN
    freqs = constants.PANDAS_FREQS
    for freq in freqs:
        # Promedio
        avg = index_transform(col, lambda x: x.mean(), index, series_id, freq, 'avg')
        actions.extend(avg.values.flatten())

        if orig_freq == freq:
            break

        # Suma
        _sum = index_transform(col, sum, index, series_id, freq, 'sum')
        actions.extend(_sum.values.flatten())

        # End of period
        eop = index_transform(col, end_of_period, index, series_id, freq, 'end_of_period')
        actions.extend(eop.values.flatten())

    return actions


def index_transform(col, transform_function, index, series_id, freq, name):
    transform_col = col.resample(freq).apply(transform_function)
    transform_df = generate_interval_transformations_df(transform_col, freq)
    result = transform_df.apply(elastic_index,
                                axis='columns',
                                args=(index, series_id, freq, name))

    handle_last_value(col, freq, result)

    return result


def handle_last_value(col, target_freq, result):
    """Borra el último valor a indexar si este no cumple con un intervalo completo de collapse
    Se considera intervalo completo al que tenga todos los valores posibles del intervalo
    target, ej: un collapse mensual -> anual debe tener valores para los 12 meses del año
    """
    handlers = {
        constants.PANDAS_QUARTER: handle_last_value_quarter,
        constants.PANDAS_MONTH: handle_last_value_month,
        constants.PANDAS_DAY: handle_last_value_daily,
    }
    orig_freq = col.index.freq
    # Si no hay handler, no hacemos nada
    if orig_freq not in handlers.keys():
        return

    last_date = col.index[-1]
    result_last_date = result.index[-1]

    handlers[orig_freq](last_date, result, result_last_date, target_freq)


# pylint: disable=W0613
def handle_last_value_quarter(last_date, result, result_last_date, target_freq):
    # Colapso quarter -> year: debe estar presente el último quarter (mes 10)
    if target_freq == constants.PANDAS_YEAR and last_date.month != 10:
        handle_incomplete_value(result)


def handle_last_value_month(last_date, result, result_last_date, target_freq):
    if target_freq == constants.PANDAS_YEAR and last_date.month != 12:
        # Colapso month -> year: debe estar presente el último mes (12)
        handle_incomplete_value(result)
    elif target_freq == constants.PANDAS_QUARTER:
        # Colapso month -> quarter: debe estar presente el último mes del quarter
        # Ese mes se puede calcular como quarter * 3 (03, 06, 09, 12)
        if last_date.month != result_last_date.quarter * 3:
            handle_incomplete_value(result)


def handle_last_value_daily(last_date, result, result_last_date, target_freq):
    if target_freq == constants.PANDAS_YEAR:
        # Colapso day -> year: debe haber valores hasta el 31/12
        if last_date.month != 12 or last_date.day != 31:
            handle_incomplete_value(result)

    elif target_freq == constants.PANDAS_QUARTER:
        # Colapso day -> quarter: debe haber valores hasta 31/03, 30/06, 30/09 o 31/12
        # El último mes del quarter se puede calcular como quarter * 3
        _, last_day = monthrange(result_last_date.year, result_last_date.quarter * 3)
        if last_date.day != last_day or last_date.month != result_last_date.quarter * 3:
            handle_incomplete_value(result)
    elif target_freq == constants.PANDAS_MONTH:
        # Colapso day -> month: debe haber valores hasta el último día del mes
        _, last_day = monthrange(result_last_date.year, result_last_date.month)
        if last_date.day != last_day:
            handle_incomplete_value(result)


def handle_incomplete_value(col):
    del col[col.index[-1]]


def end_of_period(x):
    """Itera hasta encontrarse con el último valor no nulo del data frame"""
    value = np.nan
    i = -1
    while np.isnan(value) and -i <= len(x):
        value = x.iloc[i]
        i -= 1
    return value


def generate_interval_transformations_df(col, freq):
    df = pd.DataFrame()
    df[constants.VALUE] = col
    df[constants.CHANGE] = col.diff(1)
    df[constants.PCT_CHANGE] = col.pct_change(1, fill_method=None)
    df[constants.CHANGE_YEAR_AGO] = change_a_year_ago(col, freq)
    df[constants.PCT_CHANGE_YEAR_AGO] = pct_change_a_year_ago(col, freq)
    return df


def elastic_index(row, index, series_id, freq, agg):
    """Arma el JSON entendible por el bulk request de ES y lo
    agrega a la lista de bulk_actions

    la fila tiene forma de iterable con los datos de un único
    valor de la serie: el valor real, su variación inmnediata,
    porcentual, etc
    """

    # Borrado de la parte de tiempo del timestamp
    timestamp = str(row.name)
    timestamp = timestamp[:timestamp.find('T')]
    freq = freq_pandas_to_interval(freq.freqstr)
    action = {
        "_index": index,
        "_type": settings.TS_DOC_TYPE,
        "_id": None,
        "_source": {}
    }

    source = {
        settings.TS_TIME_INDEX_FIELD: timestamp,
        'series_id': series_id,
        "interval": freq,
        "aggregation": agg
    }

    for column, value in row.iteritems():
        if value is not None and np.isfinite(value):
            # Todo: buscar método más elegante para resolver precisión incorrecta de los valores
            # Ver issue: https://github.com/datosgobar/series-tiempo-ar-api/issues/63
            # Convertir el np.float64 a string logra evitar la pérdida de precision. Luego se
            # convierte a float de Python para preservar el tipado numérico del valor
            source[column] = float(str(value))

    action['_id'] = series_id + '-' + freq + '-' + agg + '-' + timestamp
    action['_source'] = source
    return action
