#ifndef THREADSTATE_H
#define THREADSTATE_H

#include <Python.h>
#include <cstdint>

namespace __retrace {

struct ThreadState {
    PyObject_HEAD
    uint64_t m_instruction_counter;
    uint64_t m_callback_counter;
    uint64_t m_frame_counter;
    PyObject * m_thread;

    ThreadState(PyObject * thread);

    void increment();
    void set_callback_at(uint64_t counter);
};

extern PyTypeObject ThreadState_Type;

ThreadState * ThreadState_Get(PyThreadState * tstate, PyObject * main_thread);

}

#endif // THREADSTATE_H
