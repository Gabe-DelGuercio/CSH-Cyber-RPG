"""
Define RPG classes and their tier progression.

Tier 1 classes are imported from the CSV file and have no level requirement.
Tier 2 classes upgrade Tier 1 classes, Tier 3 classes upgrade Tier 2 classes,
and Tier 4 classes upgrade Tier 3 classes. Some classes are only available
after specific classes have been selected.
"""
import csv
import json

def load_classes_from_csv(file_path):
    """
    Load RPG classes from a CSV file.

    Args:
        file_path (str): The path to the CSV file containing class data.

    Returns:
        list: A list of dictionaries representing the loaded classes.
    """
    with open(file_path, newline="", encoding="utf-8-sig") as csv_file:
        classes = []
        for row in csv.DictReader(csv_file):
            row["tier"] = int(row["tier"])
            for field in ("requirements", "stats", "skills", "abilities"):
                row[field] = json.loads(row[field])
            classes.append(row)
    return classes

def get_tier_classes(tier, classes):
    """
    Get classes of a specific tier.

    Args:
        tier (int): The tier level to filter classes by.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        list: A list of dictionaries representing the classes of the specified tier.
    """
    return [class_data for class_data in classes if class_data["tier"] == tier]

def get_available_classes(selected_classes, classes):
    """
    Get available classes based on selected classes.

    Args:
        selected_classes (list): A list of selected class names.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        list: A list of dictionaries representing the available classes.
    """
    selected_classes = set(selected_classes)
    return [
        class_data
        for class_data in classes
        if class_data["name"] not in selected_classes
        and set(class_data["requirements"]).issubset(selected_classes)
    ]

def get_class_by_name(class_name, classes):
    """
    Get a class by its name.

    Args:
        class_name (str): The name of the class to retrieve.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        dict or None: A dictionary representing the class if found, otherwise None.
    """
    return next((class_data for class_data in classes if class_data["name"] == class_name), None)

def get_class_tier(class_name, classes):
    """
    Get the tier of a class by its name.

    Args:
        class_name (str): The name of the class to retrieve the tier for.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        int or None: The tier of the class if found, otherwise None.
    """
    class_data = next(
        (class_data for class_data in classes if class_data["name"] == class_name),
        None,
    )
    return class_data["tier"] if class_data is not None else None

def get_class_requirements(class_name, classes):
    """
    Get the requirements for a class by its name.

    Args:
        class_name (str): The name of the class to retrieve the requirements for.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        list or None: A list of requirements for the class if found, otherwise None.
    """
    class_data = next(
        (class_data for class_data in classes if class_data["name"] == class_name),
        None,
    )
    return class_data["requirements"] if class_data is not None else None

def get_class_description(class_name, classes):
    """
    Get the description of a class by its name.

    Args:
        class_name (str): The name of the class to retrieve the description for.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        str or None: The description of the class if found, otherwise None.
    """
    class_data = next(
        (class_data for class_data in classes if class_data["name"] == class_name),
        None,
    )
    return class_data["description"] if class_data is not None else None

def get_class_stats(class_name, classes):
    """
    Get the stats of a class by its name.

    Args:
        class_name (str): The name of the class to retrieve the stats for.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        dict or None: A dictionary representing the stats of the class if found, otherwise None.
    """
    class_data = next(
        (class_data for class_data in classes if class_data["name"] == class_name),
        None,
    )
    return class_data["stats"] if class_data is not None else None

def get_class_skills(class_name, classes):
    """
    Get the skills of a class by its name.

    Args:
        class_name (str): The name of the class to retrieve the available skills for.
        classes (list): A list of dictionaries representing the loaded classes.

        Returns:
            list or None: The class's skills if found, otherwise None.
    """
    class_data = next(
        (class_data for class_data in classes if class_data["name"] == class_name),
        None,
    )
    return class_data["skills"] if class_data is not None else None

def get_class_abilities(class_name, classes):
    """
    Get the abilities of a class by its name.

    Args:
        class_name (str): The name of the class to retrieve the abilities for.
        classes (list): A list of dictionaries representing the loaded classes.

    Returns:
        list or None: A list of abilities for the class if found, otherwise None.
    """
    class_data = next(
        (class_data for class_data in classes if class_data["name"] == class_name),
        None,
    )
    return class_data["abilities"] if class_data is not None else None