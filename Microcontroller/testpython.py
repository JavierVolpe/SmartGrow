def switch_example(value):
    match value:
        case "apple":
            return "You chose apple!"
        case "banana":
            return "You chose banana!"
        case "cherry":
            return "You chose cherry!"
        case value2 if value2.startswith("m") or value2.startswith("M"):
            return f"Your fruit starts with the letter 'm'! 1st and {value2}!"

        # case variable if variable.startswith("m"):
        #     return "Your fruit starts with the letter 'm'!"
        case _:
            return "Unknown fruit!"
# Example usage
print(switch_example("apple"))  # Output: You chose apple!
print(switch_example("mango"))  # Output: Unknown fruit!
