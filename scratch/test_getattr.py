class A:
    def __init__(self):
        self.layer = 1

i = A()
try:
    print(getattr(i, 'layer', i.get('layer', '')))
except Exception as e:
    print(f"Error: {repr(e)}")
