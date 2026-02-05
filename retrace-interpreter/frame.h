#ifndef FRAME_H
#define FRAME_H

#include <Python.h>
#include <internal/pycore_frame.h>
#include <vector>

namespace __retrace {

struct Frame {
    PyObject_HEAD
    _PyInterpreterFrame * m_frame;
    std::vector<uint64_t> m_stack_provenance;
    uint64_t m_frame_counter;

    Frame(_PyInterpreterFrame * frame, uint64_t frame_counter);

    void push_provenance(uint64_t counter);
    uint64_t pop_provenance();
    uint64_t peek_provenance(int offset = 0) const;
};

extern PyTypeObject Frame_Type;

Frame * Frame_Get(_PyInterpreterFrame * frame);
void Frame_Create(_PyInterpreterFrame * frame, uint64_t frame_counter);

}

#endif // FRAME_H
