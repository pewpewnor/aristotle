"""Example module used by tests.

This module defines a few simple classes and functions to exercise the
AST traverser and node/relationship extraction. It intentionally includes
module, class, method and function docstrings so the parser can capture
semantic text for nodes and facts.
"""


x = 42


class Animal:
    """Base class for animals.

    Animal stores a name and can speak (prints its name).
    """

    def __init__(self, name: str):
        """Initialize an Animal with a name.

        Args:
            name: human-readable name for the animal
        """
        self.name = name

    def speak(self):
        """Make the animal speak by printing its name."""
        print(self.name)


class Mammal:
    """Marker class that represents mammal-type animals."""

    pass


class Dog(Animal, Mammal):
    """A friendly dog that can bark."""

    def bark(self, words: str):
        """Bark the provided words (print them)."""
        print(words)


def greet(animal: Animal, age: int):
    """Greet an animal and report its age.

    Returns an integer example value.
    """
    print(f"Hello, {animal.speak()}, the age is {age}")
    return 10
