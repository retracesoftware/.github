#include "threadstate.h"
#include <unordered_map>
#include <new>

namespace __retrace {

// Getter for 'counter' attribute
static PyObject * ThreadState_get_counter(ThreadState *self, void *closure) {
    return PyLong_FromUnsignedLongLong(self->m_instruction_counter);
}

// Getter for 'frame_counter' attribute
static PyObject * ThreadState_get_frame_counter(ThreadState *self, void *closure) {
    return PyLong_FromUnsignedLongLong(self->m_frame_counter);
}

// Getter for 'callback_counter' attribute
static PyObject * ThreadState_get_callback_counter(ThreadState *self, void *closure) {
    return PyLong_FromUnsignedLongLong(self->m_callback_counter);
}

// Getter for 'thread' attribute
static PyObject * ThreadState_get_thread(ThreadState *self, void *closure) {
    if (self->m_thread) {
        Py_INCREF(self->m_thread);
        return self->m_thread;
    }
    Py_RETURN_NONE;
}

static PyGetSetDef ThreadState_getsetters[] = {
    {"counter", (getter)ThreadState_get_counter, nullptr, "Instruction counter", nullptr},
    {"frame_counter", (getter)ThreadState_get_frame_counter, nullptr, "Frame counter", nullptr},
    {"callback_counter", (getter)ThreadState_get_callback_counter, nullptr, "Callback counter", nullptr},
    {"thread", (getter)ThreadState_get_thread, nullptr, "Thread object", nullptr},
    {nullptr}  // Sentinel
};

PyTypeObject ThreadState_Type = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_retraceinterpreter.ThreadState",
    .tp_basicsize = sizeof(ThreadState),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_getset = ThreadState_getsetters,
};

// Map from PyThreadState to our ThreadState
static std::unordered_map<PyThreadState *, ThreadState *> thread_states;

ThreadState::ThreadState(PyObject * thread) :
    m_instruction_counter(0),
    m_callback_counter(0),
    m_frame_counter(0),
    m_thread(Py_XNewRef(thread)) {}

void ThreadState::increment() {
    m_instruction_counter++;
}

void ThreadState::set_callback_at(uint64_t counter) {
    m_callback_counter = counter;
}

ThreadState * ThreadState_Get(PyThreadState * tstate, PyObject * main_thread) {
    auto it = thread_states.find(tstate);
    if (it != thread_states.end()) {
        return it->second;
    }

    // Create new ThreadState
    void * mem = (void *)_PyObject_New(&ThreadState_Type);
    ThreadState * state = new (mem) ThreadState(main_thread);
    thread_states[tstate] = state;
    return state;
}

}
