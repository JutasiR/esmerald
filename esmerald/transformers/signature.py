"""
Signature is widely used by Pydantic and comes from the inpect library.
A lot of great work was done using the Signature and Esmerald is no exception.
"""

from inspect import Parameter
from inspect import Signature as InspectSignature
from typing import TYPE_CHECKING, Any, Generator, Optional, Set, Type

from esmerald.exceptions import ImproperlyConfigured
from esmerald.transformers.constants import CLASS_SPECIAL_WORDS, VALIDATION_NAMES
from esmerald.transformers.datastructures import EsmeraldSignature, Parameter
from esmerald.transformers.helpers import is_pydantic_constrained_field
from esmerald.transformers.utils import get_field_definition_from_param
from esmerald.utils.dependency import (
    is_dependency_field,
    should_skip_dependency_validation,
)
from pydantic import BaseModel, create_model
from pydantic.fields import Undefined

if TYPE_CHECKING:
    from pydantic.typing import AnyCallable, DictAny
    from starlette.datastructures import URL


class SignatureFactory(BaseModel):
    signature: Optional[InspectSignature]
    fn: Optional["AnyCallable"]
    fn_name: Optional[str]
    field_definitions: Optional["DictAny"]
    defaults: Optional["DictAny"]
    dependency_names: Optional[Set[str]]

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, fn: "AnyCallable", dependency_names: Set[str], **kwargs: "DictAny") -> None:
        super().__init__(**kwargs)
        if not fn or fn is None:
            raise ImproperlyConfigured("Parameter 'fn' to SignatureFactory cannot be `None`.")
        self.fn = fn
        self.signature = InspectSignature.from_callable(self.fn)
        self.fn_name = fn.__name__ if hasattr(fn, "__name__") else "anonymous"
        self.defaults = {}
        self.dependency_names = dependency_names

    def validate_missing_dependency(self, param: Parameter) -> None:
        if not is_dependency_field(param.default):
            return
        if param.optional:
            return
        field = param.default
        if field.default is not Undefined:
            return
        if param.name not in self.dependency_names:
            raise ImproperlyConfigured(
                f"Explicit dependency '{param.name}' for '{self.fn_name}' has no default value, "
                f"or provided dependency."
            )

    def get_dependency_names(self, param: Parameter) -> None:
        if is_dependency_field(param.default):
            self.dependency_names.add(param.name)

    def set_default_field(self, param: Parameter) -> None:
        if param.default_defined:
            self.defaults[param.name] = param.default

    @property
    def parameters(self) -> Generator[Parameter, None, None]:
        for name, param in self.signature.parameters.items():
            if name in CLASS_SPECIAL_WORDS:
                continue
            yield Parameter(self.fn_name, name, param)

    def skip_parameter_validation(self, param: Parameter) -> bool:
        return param.name in VALIDATION_NAMES or should_skip_dependency_validation(param.default)

    def create_signature(self) -> Type[EsmeraldSignature]:
        try:
            for param in self.parameters:
                self.validate_missing_dependency(param)
                self.get_dependency_names(param)
                self.set_default_field(param)

                if is_pydantic_constrained_field(param.default):
                    self.field_definitions[param.name] = (param.default, ...)
                if self.skip_parameter_validation(param):
                    self.field_definitions[param.name] = (Any, ...)
                self.field_definitions[param.name] = get_field_definition_from_param(param)

                model: Type["EsmeraldSignature"] = create_model(
                    self.fn_name + "_signature",
                    __base__=EsmeraldSignature,
                    **self.field_definitions,
                )
                model.return_annotation = self.signature.return_annotation
                model.dependency_names = self.dependency_names
                return model
        except TypeError as e:
            raise ImproperlyConfigured(
                f"Error creating signature for '{self.fn_name}': '{e}'."
            ) from e
