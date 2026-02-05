#include "interpreter.h"
#include "threadstate.h"
#include <new>

namespace __retrace {

PyTypeObject Interpreter_Type = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_retraceinterpreter.Interpreter",
    .tp_basicsize = sizeof(Interpreter),
};

Interpreter::Interpreter(PyThreadState * outside, PyObject * callback, PyObject * thread) :
    m_outside(outside), m_callback(Py_XNewRef(callback)), m_thread(Py_XNewRef(thread)) {}

void Install_Interpreter(PyThreadState * outside, PyObject * callback, PyObject * thread) {
    PyInterpreterState * pystate = PyInterpreterState_Get();
    PyObject * dict = PyInterpreterState_GetDict(pystate);
    if (dict) {
        void * mem = (void *)_PyObject_New(&Interpreter_Type);
        Interpreter * i = new (mem) Interpreter(outside, callback, thread);
        PyDict_SetItemString(dict, "__retrace__", (PyObject *)i);
    }
}

Interpreter * Interpreter_Get() {
    PyInterpreterState * pystate = PyInterpreterState_Get();
    PyObject * dict = PyInterpreterState_GetDict(pystate);
    if (!dict) return nullptr;
    return (Interpreter *) PyDict_GetItemString(dict, "__retrace__");
}

PyObject * Interpreter::thread_id() const {
    if (!m_outside) {
        // Running in current interpreter - no thread swap needed
        return PyObject_CallOneArg(m_thread, PyImport_GetModuleDict());
    }
    PyThreadState * current = PyThreadState_Swap(m_outside);
    if (!current) return nullptr;
    PyObject * res = PyObject_CallOneArg(m_thread, PyImport_GetModuleDict());
    if (res) {
        PyThreadState_Swap(current);
    } else {
        PyObject *exc_type, *exc_value, *exc_traceback;
        PyErr_Fetch(&exc_type, &exc_value, &exc_traceback);
        PyThreadState_Swap(current);
        PyErr_Restore(exc_type, exc_value, exc_traceback);
    }
    return res;
}

PyObject * Interpreter::callback(ThreadState * state) {
    if (!m_outside) {
        // Running in current interpreter - no thread swap needed
        return PyObject_CallOneArg(m_callback, (PyObject *)state);
    }
    PyThreadState * current = PyThreadState_Swap(m_outside);
    if (!current) return nullptr;
    PyObject * res = PyObject_CallOneArg(m_callback, (PyObject *)state);
    if (res) {
        PyThreadState_Swap(current);
    } else {
        PyObject *exc_type, *exc_value, *exc_traceback;
        PyErr_Fetch(&exc_type, &exc_value, &exc_traceback);
        PyThreadState_Swap(current);
        PyErr_Restore(exc_type, exc_value, exc_traceback);
    }
    return res;
}

}
