#include <Python.h>
#include <vector>
#include "frame.h"
#include "interpreter.h"
#include "threadstate.h"

// Forward declaration of the frame evaluation function
PyObject* RetraceFrameEvalFunction(PyThreadState *tstate, struct _PyInterpreterFrame *frame, int throwflag);

static PyObject * run_in_subinterpreter(PyObject* target, PyObject* args, PyObject* kwargs,
                                        PyObject * main_thread, PyObject * thread, PyObject * callback,
                                        uint64_t callback_at) {
    PyThreadState * current = PyThreadState_Get();
    PyThreadState * sub_interpreter = Py_NewInterpreter();
    assert(sub_interpreter);
    assert(current);

    PyInterpreterState * pystate = PyInterpreterState_Get();
    PyObject * dict = PyInterpreterState_GetDict(pystate);
    if (!dict) {
        if (!PyErr_Occurred()) {
            PyErr_SetString(PyExc_RuntimeError, "Interpreter doesn't support interpreter-specific dictionaries");
        }
        return nullptr;
    }

    __retrace::Install_Interpreter(current, callback, thread);
    __retrace::ThreadState * state = __retrace::ThreadState_Get(PyThreadState_Get(), main_thread);
    if (state && callback_at > 0) {
        state->m_callback_counter = callback_at;
    }

    _PyFrameEvalFunction original = _PyInterpreterState_GetEvalFrameFunc(pystate);
    _PyInterpreterState_SetEvalFrameFunc(pystate, RetraceFrameEvalFunction);

    PyObject * result = PyObject_Call(target, args, kwargs);

    _PyInterpreterState_SetEvalFrameFunc(pystate, original);

    PyObject *exc_type, *exc_value, *exc_traceback;
    if (!result) {
        PyErr_Fetch(&exc_type, &exc_value, &exc_traceback);
    }

    Py_EndInterpreter(sub_interpreter);
    PyThreadState_Swap(current);

    if (!result) {
        PyErr_Restore(exc_type, exc_value, exc_traceback);
    }

    return result;
}

static PyObject * run_in_current_interpreter(PyObject* target, PyObject* args, PyObject* kwargs,
                                              PyObject * main_thread, PyObject * thread, PyObject * callback,
                                              uint64_t callback_at) {
    PyInterpreterState * pystate = PyInterpreterState_Get();

    PyObject * dict = PyInterpreterState_GetDict(pystate);
    if (!dict) {
        if (!PyErr_Occurred()) {
            PyErr_SetString(PyExc_RuntimeError, "Interpreter doesn't support interpreter-specific dictionaries");
        }
        return nullptr;
    }

    __retrace::Install_Interpreter(nullptr, callback, thread);  // nullptr = no thread swap
    __retrace::ThreadState * state = __retrace::ThreadState_Get(PyThreadState_Get(), main_thread);
    if (state && callback_at > 0) {
        state->m_callback_counter = callback_at;
    }

    _PyFrameEvalFunction original = _PyInterpreterState_GetEvalFrameFunc(pystate);
    _PyInterpreterState_SetEvalFrameFunc(pystate, RetraceFrameEvalFunction);

    PyObject * result = PyObject_Call(target, args, kwargs);

    _PyInterpreterState_SetEvalFrameFunc(pystate, original);

    return result;
}

static PyObject * run(PyObject* self, PyObject* args, PyObject* kwargs) {
    static const char* keywords[] = {
        "target", "args", "kwargs", "main_thread", "thread", "callback",
        "use_subinterpreter", "callback_at", nullptr
    };

    PyObject * target;
    PyObject * target_args;
    PyObject * target_kwargs = nullptr;
    PyObject * main_thread = nullptr;
    PyObject * thread = nullptr;
    PyObject * callback = nullptr;
    int use_subinterpreter = 1;  // Default to True for backwards compatibility
    unsigned long long callback_at = 1;  // Default to callback at instruction 1

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOOOOO|pK", (char **)keywords,
        &target, &target_args, &target_kwargs, &main_thread, &thread, &callback,
        &use_subinterpreter, &callback_at)) {
        return nullptr;
    }

    if (use_subinterpreter) {
        return run_in_subinterpreter(target, target_args, target_kwargs, main_thread, thread, callback, callback_at);
    } else {
        return run_in_current_interpreter(target, target_args, target_kwargs, main_thread, thread, callback, callback_at);
    }
}

static PyMethodDef methods[] = {
    {"run", (PyCFunction)run, METH_VARARGS | METH_KEYWORDS,
     "Run target with retrace interpreter.\n\n"
     "Args:\n"
     "    target: Callable to execute\n"
     "    args: Positional arguments tuple\n"
     "    kwargs: Keyword arguments dict\n"
     "    main_thread: Thread ID function for main thread\n"
     "    thread: Thread ID function\n"
     "    callback: Function called at instruction boundaries\n"
     "    use_subinterpreter: If True, run in sub-interpreter (default True)\n"
     "    callback_at: Instruction count to trigger first callback (default 1)\n"
    },
    {nullptr, nullptr, 0, nullptr}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_retraceinterpreter",
    "Retrace interpreter module for provenance tracking",
    -1,
    methods
};

PyMODINIT_FUNC PyInit__retraceinterpreter(void) {
    if (PyType_Ready(&__retrace::Interpreter_Type) < 0) return nullptr;
    if (PyType_Ready(&__retrace::ThreadState_Type) < 0) return nullptr;
    if (PyType_Ready(&__retrace::Frame_Type) < 0) return nullptr;

    return PyModule_Create(&moduledef);
}
