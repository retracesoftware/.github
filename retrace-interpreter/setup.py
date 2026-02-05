from setuptools import setup, Extension
import sysconfig

# Get Python include paths
python_include = sysconfig.get_path('include')
python_platinclude = sysconfig.get_path('platinclude')

# CPython internal headers (for internal/pycore_frame.h)
# These are typically in the same location as regular includes for debug builds
# or need to be obtained from the Python source

ext_module = Extension(
    '_retraceinterpreter',
    sources=[
        '_retraceinterpreter.cpp',
        'interpreter.cpp',
        'threadstate.cpp',
        'frame.cpp',
        'opcodes.cpp',
    ],
    include_dirs=[
        '.',
        python_include,
        python_platinclude,
    ],
    extra_compile_args=[
        '-std=c++17',
        '-g',  # Debug symbols
        '-O0',  # No optimization for debugging
    ],
    language='c++',
)

setup(
    name='retraceinterpreter',
    version='0.1.0',
    description='Retrace interpreter for provenance tracking',
    ext_modules=[ext_module],
)
