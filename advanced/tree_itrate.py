class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


class TreeIterator:
    def __init__(self, root, order="preorder"):
        self.order = order
        self._items = []
        self._build(root)
        self._index = 0

    def _build(self, node):
        if node is None:
            return

        if self.order == "preorder":
            self._items.append(node.value)
            self._build(node.left)
            self._build(node.right)
        elif self.order == "inorder":
            self._build(node.left)
            self._items.append(node.value)
            self._build(node.right)
        elif self.order == "postorder":
            self._build(node.left)
            self._build(node.right)
            self._items.append(node.value)
        else:
            raise ValueError(f"Unknown order: {self.order}")

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._items):
            raise StopIteration
        value = self._items[self._index]
        self._index += 1
        return value


# Build the tree
root = Node(1)
two = Node(2)
three = Node(3)
four = Node(4)
five = Node(5)

root.left = two
root.right = three
two.left = four
two.right = five

# Test it
print("Pre-order: ", list(TreeIterator(root, "preorder")))
print("In-order:  ", list(TreeIterator(root, "inorder")))
print("Post-order:", list(TreeIterator(root, "postorder")))