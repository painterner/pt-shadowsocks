import codecs
from setuptools import setup


with codecs.open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="ptshadowsocks",
    version="2.8.2",
    license='http://www.apache.org/licenses/LICENSE-2.0',
    description="A fast tunnel proxy that help you get through firewalls",
    author='clowwindy',
    author_email='clowwindy42@gmail.com',
    url='https://github.com/shadowsocks/shadowsocks',
    packages=['ptshadowsocks', 'ptshadowsocks.cryptolib', 'ptshadowsocks.libs', 'ptshadowsocks.protocol'],
    package_data={
        'ptshadowsocks': ['README.rst', 'LICENSE']
    },
    install_requires=[],
    entry_points="""
    [console_scripts]
    sslocal = ptshadowsocks.local:main
    ssserver = ptshadowsocks.server:main
    """,
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: Proxy Servers',
    ],
    long_description=long_description,
)
