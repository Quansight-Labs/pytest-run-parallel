#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* This extension module can be built in two modes:
 * 1. Default: properly configured to not require the GIL
 *    and should not trigger GIL enabling behavior.
 * 2. With ENABLE_GIL defined: triggers GIL enabling behavior
 *    in free-threaded builds by not using the Py_mod_gil slot.
 */

static PyObject *
test_function(PyObject *self, PyObject *args)
{
    /* This function doesn't do anything special. The difference is in
     * how the module is configured regarding GIL requirements.
     */
    Py_RETURN_NONE;
}

static PyMethodDef gil_test_methods[] = {
    {"test_function", test_function, METH_NOARGS, "Test function"},
    {NULL, NULL, 0, NULL}
};

static PyModuleDef_Slot gil_test_slots[] = {
#ifndef ENABLE_GIL
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL}
};

static struct PyModuleDef gil_test_module = {
    PyModuleDef_HEAD_INIT,
#ifndef ENABLE_GIL
    "gil_disable",
#else
    "gil_enable",
#endif
    NULL,
    0,
    gil_test_methods,
    gil_test_slots,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
#ifndef ENABLE_GIL
PyInit_gil_disable(void)
#else
PyInit_gil_enable(void)
#endif
{
    return PyModuleDef_Init(&gil_test_module);
}
