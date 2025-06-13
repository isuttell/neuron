"""Unit tests for the dice tool."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from neuron_server.tools.dice_tool import DiceRoll, DiceTool, parse_dice_expression


class TestDiceRoll:
    """Tests for the DiceRoll model."""

    def test_valid_dice_roll(self) -> None:
        """Test valid dice roll parameters."""
        # Test with minimum values
        min_count = 1
        min_sides = 2
        dice_roll = DiceRoll(count=min_count, sides=min_sides)
        assert dice_roll.count == min_count
        assert dice_roll.sides == min_sides
        assert dice_roll.modifier is None

        # Test with modifier
        count = 3
        sides = 6
        modifier = 2
        dice_roll = DiceRoll(count=count, sides=sides, modifier=modifier)
        assert dice_roll.count == count
        assert dice_roll.sides == sides
        assert dice_roll.modifier == modifier

    def test_invalid_dice_roll_count(self) -> None:
        """Test invalid dice count validation."""
        with pytest.raises(ValidationError):
            DiceRoll(count=0, sides=6)  # count must be >= 1

        with pytest.raises(ValidationError):
            DiceRoll(count=-1, sides=6)  # count must be >= 1

    def test_invalid_dice_roll_sides(self) -> None:
        """Test invalid dice sides validation."""
        with pytest.raises(ValidationError):
            DiceRoll(count=1, sides=1)  # sides must be >= 2

        with pytest.raises(ValidationError):
            DiceRoll(count=1, sides=0)  # sides must be >= 2

        with pytest.raises(ValidationError):
            DiceRoll(count=1, sides=-6)  # sides must be >= 2


class TestParseDiceExpression:
    """Tests for the parse_dice_expression function."""

    def test_basic_dice_expression(self) -> None:
        """Test parsing basic dice expressions."""
        # Test simple expression
        simple_count = 1
        simple_sides = 6
        result = parse_dice_expression(f"{simple_count}d{simple_sides}")
        assert result.count == simple_count
        assert result.sides == simple_sides
        assert result.modifier is None

        # Test multi-dice expression
        multi_count = 3
        multi_sides = 8
        result = parse_dice_expression(f"{multi_count}d{multi_sides}")
        assert result.count == multi_count
        assert result.sides == multi_sides
        assert result.modifier is None

        # Test large numbers
        large_count = 20
        large_sides = 100
        result = parse_dice_expression(f"{large_count}d{large_sides}")
        assert result.count == large_count
        assert result.sides == large_sides
        assert result.modifier is None

    def test_dice_expression_with_modifiers(self) -> None:
        """Test parsing dice expressions with modifiers."""
        # Test positive modifier
        pos_count = 2
        pos_sides = 6
        pos_modifier = 3
        result = parse_dice_expression(f"{pos_count}d{pos_sides}+{pos_modifier}")
        assert result.count == pos_count
        assert result.sides == pos_sides
        assert result.modifier == pos_modifier

        # Test negative modifier
        neg_count = 4
        neg_sides = 10
        neg_modifier = -2
        result = parse_dice_expression(f"{neg_count}d{neg_sides}{neg_modifier}")
        assert result.count == neg_count
        assert result.sides == neg_sides
        assert result.modifier == neg_modifier

        # Test large modifier
        large_mod_count = 1
        large_mod_sides = 20
        large_modifier = 10
        dice_expr = f"{large_mod_count}d{large_mod_sides}+{large_modifier}"
        result = parse_dice_expression(dice_expr)
        assert result.count == large_mod_count
        assert result.sides == large_mod_sides
        assert result.modifier == large_modifier

    def test_invalid_dice_expressions(self) -> None:
        """Test parsing invalid dice expressions."""
        # These expressions should definitely fail the regex pattern
        invalid_expressions = [
            "",  # Empty string
            "d20",  # Missing count
            "4d",  # Missing sides
            "4+2",  # Missing 'd'
            "4k6",  # Invalid separator
            "d6+3",  # Missing count
            "hello",  # Completely invalid
        ]

        for expression in invalid_expressions:
            with pytest.raises(ValueError):
                parse_dice_expression(expression)

    def test_incomplete_modifiers_in_regex(self) -> None:
        """
        Test for expressions with incomplete modifiers.

        Note: The current implementation actually accepts expressions like "4d6+"
        because the modifier part of the regex is optional. This test documents
        this behavior, which could be considered a bug that should be fixed.
        """
        # These expressions are accepted by the current implementation
        # but might be considered invalid from a user perspective
        expressions_with_incomplete_modifiers = [
            "4d6+",  # Plus sign without a number
            "4d6-",  # Minus sign without a number
        ]

        for expression in expressions_with_incomplete_modifiers:
            result = parse_dice_expression(expression)
            assert result.count > 0
            assert result.sides > 0
            # The modifier is None because the regex doesn't match the
            # incomplete modifier
            assert result.modifier is None


class TestDiceTool:
    """Tests for the DiceTool."""

    def test_run_single_dice(self) -> None:
        """Test running the tool with a single dice expression."""
        with patch("random.randint") as mock_randint:
            # Mock the random.randint to return a fixed value for testing
            mock_randint.return_value = 4

            dice_tool = DiceTool()
            result = dice_tool._run(["1d6"])

            mock_randint.assert_called_once_with(1, 6)
            assert "Rolled 1d6:" in result
            assert "results=4" in result
            assert "total=4" in result

    def test_run_multiple_dice(self) -> None:
        """Test running the tool with multiple dice expressions."""
        with patch("random.randint") as mock_randint:
            # Return different values for different calls
            mock_randint.side_effect = [3, 5, 2]

            dice_tool = DiceTool()
            result = dice_tool._run(["2d6", "1d4"])

            # Should be called 3 times: twice for 2d6 and once for 1d4
            expected_calls = 3
            assert mock_randint.call_count == expected_calls

            # Check that both dice results are in the output
            assert "Rolled 2d6:" in result
            assert "Rolled 1d4:" in result

            # Make sure there are two lines in the result
            expected_lines = 2
            assert len(result.split("\n")) == expected_lines

    def test_run_with_modifiers(self) -> None:
        """Test running the tool with dice expressions that include modifiers."""
        with patch("random.randint") as mock_randint:
            mock_randint.side_effect = [4]  # Just one roll

            dice_tool = DiceTool()
            result = dice_tool._run(["1d20+5"])

            mock_randint.assert_called_once_with(1, 20)
            assert "Rolled 1d20+5:" in result
            assert "results=4+5" in result
            assert "total=9" in result  # 4 from the roll + 5 from the modifier

    def test_run_with_multiple_dice_same_expression(self) -> None:
        """Test running the tool with multiple dice in a single expression."""
        with patch("random.randint") as mock_randint:
            # 3 dice with 8 sides each
            mock_randint.side_effect = [6, 3, 8]

            dice_tool = DiceTool()
            result = dice_tool._run(["3d8"])

            expected_dice_count = 3
            assert mock_randint.call_count == expected_dice_count
            assert "Rolled 3d8:" in result
            assert "results=6+3+8" in result
            assert "total=17" in result  # 6 + 3 + 8 = 17

    def test_run_complex_scenario(self) -> None:
        """Test running the tool with a complex combination of expressions."""
        with patch("random.randint") as mock_randint:
            # Multiple expressions with different numbers of dice
            mock_randint.side_effect = [20, 4, 2, 5, 3]  # 1d20, 2d6, 2d4

            dice_tool = DiceTool()
            result = dice_tool._run(["1d20+10", "2d6-1", "2d4"])

            expected_dice_count = 5  # 1 + 2 + 2
            assert mock_randint.call_count == expected_dice_count

            assert "Rolled 1d20+10:" in result
            assert "Rolled 2d6-1:" in result
            assert "Rolled 2d4:" in result

            # Check totals
            assert "total=30" in result  # 20 + 10 = 30
            assert "total=5" in result  # 4 + 2 - 1 = 5
            assert "total=8" in result  # 5 + 3 = 8
