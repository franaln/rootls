from glob import glob
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='rootutils',
    version='0.2.1',
    description='',
    url='https://github.com/franaln/rootutils',
    author='Francisco Alonso',
    author_email='franaln@gmail.com',
    license='',
    packages=['rootutils',],
    scripts=glob('scripts/*'),
    zip_safe=False,
)
