#ifndef INTERPRETER_H
#define INTERPRETER_H

#include <Python.h>

namespace __retrace {

struct ThreadState;

struct Interpreter {
    PyObject_HEAD
    PyThreadState * m_outside;
    PyObject * m_callback;
    PyObject * m_thread;

    Interpreter(PyThreadState * outside, PyObject * callback, PyObject * thread);

    PyObject * callback(ThreadState * state);
    PyObject * thread_id() const;
};

extern PyTypeObject Interpreter_Type;

void Install_Interpreter(PyThreadState * outside, PyObject * callback, PyObject * thread);
Interpreter * Interpreter_Get();

}

// Frame evaluation function
PyObject* RetraceFrameEvalFunction(PyThreadState *tstate, struct _PyInterpreterFrame *frame, int throwflag);

#endif // INTERPRETER_H
