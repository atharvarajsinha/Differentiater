import os
import sys
import json


def calculate(a, b, c):
    return a + b + c


def greet(name):
    message = f"Hello, {name}!"
    print(message)


username = "Rahul"
print("Hello World")
total = calculate(1, 2, 3)
print(json.dumps({"total": total}))
