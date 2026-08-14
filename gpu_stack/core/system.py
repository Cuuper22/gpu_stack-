"""
core/system.py
==============

System: a named collection of Variables and Equations at one scope.

Systems nest, forming a containment tree that mirrors the physical stack:
a hyperscaler contains clusters, a cluster contains racks, a rack contains
nodes, a node contains GPUs, a GPU contains SMs. `walk()` visits a system
and everything under it, which is how `all_variables()` and
`all_equations()` gather the contents of a whole subtree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union, Iterable

from .registry import Registry
from .variable import Variable
from .equation import Equation


@dataclass
class System:
    name: str
    scope: str
    description: str = ""
    variables: List[Variable] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    subsystems: List["System"] = field(default_factory=list)

    def __post_init__(self):
        Registry.register_system(self)

    def add(self, obj: Union[Variable, Equation, "System"]) -> None:
        if isinstance(obj, Variable):
            self.variables.append(obj)
        elif isinstance(obj, Equation):
            self.equations.append(obj)
        elif isinstance(obj, System):
            self.subsystems.append(obj)
        else:
            raise TypeError(type(obj))

    def add_all(self, items: Iterable[Union[Variable, Equation, "System"]]) -> None:
        for x in items:
            self.add(x)

    def walk(self) -> Iterable["System"]:
        yield self
        for sub in self.subsystems:
            yield from sub.walk()

    def all_variables(self) -> List[Variable]:
        out: List[Variable] = []
        for s in self.walk():
            out.extend(s.variables)
        return out

    def all_equations(self) -> List[Equation]:
        out: List[Equation] = []
        for s in self.walk():
            out.extend(s.equations)
        return out


__all__ = ["System"]
