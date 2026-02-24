import py_trees

print("py_trees 模块属性:")
print([x for x in dir(py_trees) if not x.startswith('_')])

print("\npy_trees.trees 模块属性:")
print([x for x in dir(py_trees.trees) if not x.startswith('_')])

print("\npy_trees.behaviour.Behaviour 方法:")
print([x for x in dir(py_trees.behaviour.Behaviour) if not x.startswith('_')])
