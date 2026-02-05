#include <Python.h>
#include <internal/pycore_frame.h>
#include <opcode.h>
#include <stdio.h>
#include "interpreter.h"
#include "threadstate.h"
#include "frame.h"

// Default CPython frame evaluation function
extern "C" PyObject* _PyEval_EvalFrameDefault(PyThreadState *tstate, _PyInterpreterFrame *frame, int throwflag);

// Debug flag - set to true to see trace output
static bool g_debug = false;

// Track if global tracing is set up
static bool g_tracing_enabled = false;

// Trace function called for each line/instruction
static int trace_callback(PyObject *obj, PyFrameObject *pyframe, int what, PyObject *arg) {
    __retrace::Interpreter * interpreter = __retrace::Interpreter_Get();
    if (!interpreter) return 0;

    __retrace::ThreadState * state = __retrace::ThreadState_Get(PyThreadState_Get(), nullptr);
    if (!state) return 0;

    // Count instructions for opcode events
    if (what == PyTrace_OPCODE) {
        state->m_instruction_counter++;

        if (g_debug && state->m_instruction_counter <= 10) {
            fprintf(stderr, "TRACE: instr=%lu, callback_at=%lu\n",
                    (unsigned long)state->m_instruction_counter,
                    (unsigned long)state->m_callback_counter);
        }

        // Check if we should call the callback
        if (state->m_callback_counter > 0 &&
            state->m_instruction_counter >= state->m_callback_counter) {

            if (g_debug) {
                fprintf(stderr, "TRACE: triggering callback at %lu\n",
                        (unsigned long)state->m_instruction_counter);
            }

            PyObject * cb_result = interpreter->callback(state);
            if (cb_result) {
                if (PyLong_Check(cb_result)) {
                    state->m_callback_counter = PyLong_AsUnsignedLongLong(cb_result);
                    if (g_debug) {
                        fprintf(stderr, "TRACE: next callback at %lu\n",
                                (unsigned long)state->m_callback_counter);
                    }
                } else if (cb_result == Py_None) {
                    state->m_callback_counter = 0;  // Disable callbacks
                }
                Py_DECREF(cb_result);
            } else {
                // Callback raised an exception - stop tracing
                return -1;
            }
        }
    }
    // Also enable opcode tracing for new frames (call events)
    else if (what == PyTrace_CALL) {
        if (pyframe) {
            pyframe->f_trace_opcodes = 1;
        }
    }

    return 0;  // Continue tracing
}

// Local trace function to enable opcode tracing on each frame
static PyObject* local_trace(PyObject *obj, PyFrameObject *pyframe, int what, PyObject *arg) {
    // Enable opcode tracing on this frame
    if (pyframe) {
        pyframe->f_trace_opcodes = 1;
    }
    // Return a trace function to keep tracing
    Py_INCREF(obj);
    return obj;
}

PyObject* RetraceFrameEvalFunction(PyThreadState *tstate, struct _PyInterpreterFrame *frame, int throwflag) {
    // Get our interpreter state
    __retrace::Interpreter * interpreter = __retrace::Interpreter_Get();
    if (!interpreter) {
        return _PyEval_EvalFrameDefault(tstate, frame, throwflag);
    }

    // Get or create our thread state
    __retrace::ThreadState * state = __retrace::ThreadState_Get(tstate, nullptr);
    if (!state) {
        return _PyEval_EvalFrameDefault(tstate, frame, throwflag);
    }

    // Get or create our frame wrapper
    __retrace::Frame * retrace_frame = __retrace::Frame_Get(frame);
    if (!retrace_frame) {
        __retrace::Frame_Create(frame, state->m_frame_counter);
        retrace_frame = __retrace::Frame_Get(frame);
        state->m_frame_counter++;
    }

    // Set up global tracing on first frame with callbacks enabled
    if (!g_tracing_enabled && state->m_callback_counter > 0) {
        if (g_debug) {
            fprintf(stderr, "EVAL: enabling global tracing, callback_at=%lu\n",
                    (unsigned long)state->m_callback_counter);
        }
        PyEval_SetTrace(trace_callback, Py_None);
        g_tracing_enabled = true;
    }

    // Enable opcode tracing on this specific frame
    if (state->m_callback_counter > 0) {
        PyFrameObject *pyframe = frame->frame_obj;
        if (pyframe) {
            pyframe->f_trace_opcodes = 1;
            if (pyframe->f_trace == NULL) {
                Py_INCREF(Py_None);
                pyframe->f_trace = Py_None;
            }
        }
    }

    // Call the default evaluation function
    PyObject * result = _PyEval_EvalFrameDefault(tstate, frame, throwflag);

    return result;
}

// Function to reset tracing state (called when interpreter finishes)
void ResetTracingState() {
    if (g_tracing_enabled) {
        PyEval_SetTrace(nullptr, nullptr);
        g_tracing_enabled = false;
    }
}
