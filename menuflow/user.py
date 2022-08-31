from __future__ import annotations

from typing import Any, Dict, cast

from mautrix.types import UserID

from .db.user import User as DBUser
from .variable import Variable


class User(DBUser):

    by_user_id: Dict[UserID, "User"] = {}
    variables_data: Dict[str, Any] = {}

    variables: Dict[str, Variable] = {}

    def __init__(self, user_id: UserID, context: str, state: str) -> None:
        super().__init__(user_id=user_id, context=context, state=state)

    def _add_to_cache(self) -> None:
        if self.user_id:
            self.by_user_id[self.user_id] = self

    async def load_variables(self):
        for variable in await Variable.all_variables_by_fk_user(self.id):
            self.variables_data[variable.variable_id] = variable.value
            self.variables[variable.variable_id] = variable

    # @property
    # def phone(self) -> str | None:
    #     user_match = match("^@(?P<user_prefix>.+)_(?P<number>[0-9]{8,}):.+$", self.user_id)
    #     if user_match:
    #         return user_match.group("number")

    @classmethod
    async def get_by_user_id(cls, user_id: UserID, create: bool = True) -> "User" | None:
        """It gets a user from the database, or creates one if it doesn't exist

        Parameters
        ----------
        user_id : UserID
            The user's ID.
        create : bool, optional
            If True, the user will be created if it doesn't exist.

        Returns
        -------
            The user object

        """
        try:
            return cls.by_user_id[user_id]
        except KeyError:
            pass

        user = cast(cls, await super().get_by_user_id(user_id))

        if user is not None:
            user._add_to_cache()
            await user.load_variables()
            return user

        if create:
            user = cls(user_id, "message_1", "SHOW_MESSAGE")
            await user.insert()
            user._add_to_cache()
            await user.load_variables()
            return user

    async def get_varibale(self, variable_id: str) -> Variable | None:
        """This function returns a variable object from the database if it exists,
        otherwise it returns None

        Parameters
        ----------
        variable_id : str
            The variable ID.

        Returns
        -------
            A variable object

        """
        try:
            return self.variables[variable_id]
        except KeyError:
            pass

        variable = await Variable.get(fk_user=self.id, variable_id=variable_id)

        if not variable:
            return

        return variable

    async def set_variable(self, variable_id: str, value: Any):
        """It creates a new variable object, adds it to the user's variables dictionary,
        and then inserts it into the database

        Parameters
        ----------
        variable_id : str
            The variable's name.
        value : Any
            The value of the variable.

        """
        variable = Variable(variable_id=variable_id, value=value, fk_user=self.id)

        self.variables[variable_id] = variable

        await variable.insert()

    async def update_menu(self, context: str):
        """It updates the menu's state and context, and then adds it to the cache

        Parameters
        ----------
        context : str
            The context of the menu. This is used to determine what the menu is for.

        Returns
        -------
            The return value is a list of dictionaries.

        """
        if not context:
            return

        self.context = context

        if context.startswith("#pipeline"):
            self.state = "VALIDATE_PIPE"

        if context.startswith("#message"):
            self.state = "SHOW_MESSAGE"

        await self.update(context=self.context, state=self.state)
        self._add_to_cache()
