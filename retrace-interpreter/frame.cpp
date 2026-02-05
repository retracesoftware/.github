#include "frame.h"
#include <unordered_map>
#include <new>

namespace __retrace {

PyTypeObject Frame_Type = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_retraceinterpreter.Frame",
    .tp_basicsize = sizeof(Frame),
};

// Map from _PyInterpreterFrame to our Frame
static std::unordered_map<_PyInterpreterFrame *, Frame *> frames;

Frame::Frame(_PyInterpreterFrame * frame, uint64_t frame_counter) :
    m_frame(frame),
    m_frame_counter(frame_counter) {}

void Frame::push_provenance(uint64_t counter) {
    m_stack_provenance.push_back(counter);
}

uint64_t Frame::pop_provenance() {
    if (m_stack_provenance.empty()) return 0;
    uint64_t val = m_stack_provenance.back();
    m_stack_provenance.pop_back();
    return val;
}

uint64_t Frame::peek_provenance(int offset) const {
    if (offset < 0 || (size_t)offset >= m_stack_provenance.size()) return 0;
    return m_stack_provenance[m_stack_provenance.size() - 1 - offset];
}

Frame * Frame_Get(_PyInterpreterFrame * frame) {
    auto it = frames.find(frame);
    if (it != frames.end()) {
        return it->second;
    }
    return nullptr;
}

void Frame_Create(_PyInterpreterFrame * frame, uint64_t frame_counter) {
    void * mem = (void *)_PyObject_New(&Frame_Type);
    Frame * f = new (mem) Frame(frame, frame_counter);
    frames[frame] = f;
}

}
