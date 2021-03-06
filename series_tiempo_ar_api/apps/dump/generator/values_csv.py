from series_tiempo_ar_api.apps.dump import constants
from series_tiempo_ar_api.apps.dump.generator.dump_csv_writer import CsvDumpWriter
from series_tiempo_ar_api.apps.dump.models import DumpFile
from .abstract_dump_gen import AbstractDumpGenerator


class ValuesCsvGenerator(AbstractDumpGenerator):
    filename = DumpFile.FILENAME_VALUES

    def generate(self):
        filepath = self.get_file_path()
        CsvDumpWriter(self.task, self.fields, self.values_csv_row, f'{self.catalog} values csv')\
            .write(filepath, constants.VALUES_HEADER)

        self.write(filepath, self.filename, zip_file=True)

    @staticmethod
    def values_csv_row(value, fields, field, periodicity):
        return [
            fields[field]['dataset'].catalog.identifier,
            fields[field]['dataset'].identifier,
            fields[field]['distribution'].identifier,
            field,
            value[0].date(),  # Index
            value[1],  # value
            periodicity,
        ]
