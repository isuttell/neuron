from langchain.tools import BaseTool
from typing import List, Type
import subprocess
from pydantic import BaseModel, Field
import random
import re
from neuron_server.logger import logger


class DiceRoll(BaseModel):
    count: int = Field(description="The number of dice to roll", min=1, default=1)
    sides: int = Field(description="The number of sides on the dice", min=2)
    modifier: int | None = Field(
        description="An optional modifier to add to the total", default=None
    )


def parse_dice_expression(expression: str) -> DiceRoll:
    """
    Parses a dice expression (e.g., '2d6+1') into its components: number of dice, sides of dice, and modifier.

    Args:
        expression (str): The dice expression to parse.

    Returns:
        dict: A dictionary containing 'num_dice', 'sides', and 'modifier'.
    """

    # Regular expression to match the dice expression
    pattern = r"(?P<count>\d+)d(?P<sides>\d+)(?:(?P<modifier>[+-]\d+))?"
    match = re.match(pattern, expression)

    if not match:
        raise ValueError(f"Invalid dice expression: {expression}")

    count = int(match.group("count"))
    sides = int(match.group("sides"))
    modifier = int(match.group("modifier")) if match.group("modifier") else None

    return DiceRoll(count=count, sides=sides, modifier=modifier)


class DiceToolArgs(BaseModel):
    dice: List[str] = Field(
        description="A list of strings representing dice expressions, e.g. '1d20', '1d4', '5d6+3'.  The example '2d6+1' indicates rolling 2 dice, each with 6 sides, and adding a modifier of +1 to the total. The format consists of three parts: the number of dice (2), the letter 'd' to indicate dice, the number of sides on each die (6), and an optional modifier (+1). Must include at least one dice expression."
    )


class DiceTool(BaseTool):
    name: str = "dice"
    description: str = (
        """
Roll virtual dice and return the individual results of each dice and total. Use this tool to simulate dice rolls for role-playing games, tabletop games, and other applications such as helping the user make a choice. Always show the results of each dice roll to the user. Always include at least one dice expression.
""".strip()
    )

    args_schema: Type[DiceToolArgs] = DiceToolArgs

    def _run(self, dice: List[str]) -> str:
        rolls = [parse_dice_expression(d) for d in dice]
        role_results: List[List[int]] = [
            [random.randint(1, roll.sides) for _ in range(roll.count)]
            + ([roll.modifier] if roll.modifier else [])
            for roll in rolls
        ]
        totals = [sum(r) for r in role_results]
        results = list(zip(dice, role_results, totals))
        result = [
            f"Rolled {dice}: results={'+'.join([str(result) for result in results])} total={total}"
            for dice, results, total in results
        ]
        for res in result:
            logger.debug(res)
        return "\n".join(result)
