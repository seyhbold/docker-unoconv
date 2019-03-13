import os
import subprocess
import unittest

from fs import open_fs
from celery import Celery, group
import magic
from fs.copy import copy_file
from parameterized import parameterized

app = Celery('test_generators')
app.config_from_object('celery_unoconv.celeryconfig')
app.conf.update({'broker_url': 'amqp://guest:guest@localhost:5672'})

generate_preview_jpg = app.signature('celery_unoconv.tasks.generate_preview_jpg')
generate_preview_png = app.signature('celery_unoconv.tasks.generate_preview_png')
generate_pdf = app.signature('celery_unoconv.tasks.generate_pdf')

example_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('example-files') for f in filenames]


class TestFile(unittest.TestCase):

    BUCKET_NAME_INPUT = 'unoconv-input'
    BUCKET_NAME_OUTPUT = 'unoconv-output'

    INPUT_FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://localhost:9000'
    INPUT_FS_URL = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://minio:9000'
    OUTPUT_FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_OUTPUT}?endpoint_url=http://localhost:9000'
    OUTPUT_FS_URL = f's3://minio:minio123@{BUCKET_NAME_OUTPUT}?endpoint_url=http://minio:9000'

    def setUp(self):
        with open_fs(self.INPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()
        with open_fs(self.OUTPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()

    def tearDown(self):
        with open_fs(self.INPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()
        with open_fs(self.OUTPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()

    @parameterized.expand([('jpg',), ('png',), ('pdf',)])
    def test_unsupported(self, output_format: str):
        if output_format == 'jpg':
            generator = generate_preview_jpg
        elif output_format == 'png':
            generator = generate_preview_png
        elif output_format == 'pdf':
            generator = generate_pdf
        else:
            raise RuntimeError('Unsupported output format {}.'.format(output_format))

        task = generator.clone(
            kwargs={
                'input_fs_url': 'osfs:///',
                'input_file': '/dev/null',
                'output_fs_url': self.OUTPUT_FS_URL,
                'output_file': f'output.{output_format}',
                'mime_type': 'application/octet-stream',
                'extension': '.unsupported',
                'timeout': 10,
            })

        self.assertRaises(ValueError, lambda: task.apply_async().get())

    @parameterized.expand([('jpg',), ('png',), ('pdf',)])
    def test_input_file_not_found(self, output_format: str):
        if output_format == 'jpg':
            generator = generate_preview_jpg
        elif output_format == 'png':
            generator = generate_preview_png
        elif output_format == 'pdf':
            generator = generate_pdf
        else:
            raise RuntimeError('Unsupported output format {}.'.format(output_format))

        task = generator.clone(
            kwargs={
                'input_fs_url': 'osfs:///',
                'input_file': 'does-not-exist',
                'output_fs_url': self.OUTPUT_FS_URL,
                'output_file': f'output.{output_format}',
                'mime_type': 'application/vnd.oasis.opendocument.text',
                'extension': '.odt',
                'timeout': 10,
            })

        self.assertRaises(FileNotFoundError, lambda: task.apply_async().get())

    @parameterized.expand([('jpg',), ('png',), ('pdf',)])
    def test_output_wrong_fs(self, output_format: str):
        if output_format == 'jpg':
            generator = generate_preview_jpg
        elif output_format == 'png':
            generator = generate_preview_png
        elif output_format == 'pdf':
            generator = generate_pdf
        else:
            raise RuntimeError('Unsupported output format {}.'.format(output_format))

        task = generator.clone(
            kwargs={
                'input_fs_url': 'osfs:///',
                'input_file': '/dev/null',
                'output_fs_url': 'this-is-invalid',
                'output_file': f'output.{output_format}',
                'mime_type': 'application/vnd.oasis.opendocument.text',
                'extension': '.odt',
                'timeout': 10,
            })

        self.assertRaises(RuntimeError, lambda: task.apply_async().get())

    @parameterized.expand([('jpg',), ('png',)])
    def test_wrong_dimensions(self, output_format: str):
        if output_format == 'jpg':
            generator = generate_preview_jpg
        elif output_format == 'png':
            generator = generate_preview_png
        else:
            raise RuntimeError('Unsupported output format {}.'.format(output_format))

        for height, width in [(None, 800), (800, None)]:
            task = generator.clone(
                kwargs={
                    'input_fs_url': 'osfs:///',
                    'input_file': '/dev/null',
                    'output_fs_url': self.OUTPUT_FS_URL,
                    'output_file': f'output.{output_format}',
                    'mime_type': 'application/vnd.oasis.opendocument.text',
                    'extension': '.odt',
                    'height': height,
                    'width': width,
                    'timeout': 10,
                })

            self.assertRaises(ValueError, lambda: task.apply_async().get())


if __name__ == '__main__':
    unittest.main()