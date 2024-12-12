def write_to_txt(file_name, content):
    """
    Writes the given content into a text file.

    Args:
        file_name (str): The name of the text file to write to.
        content (str): The content to write into the file.

    Returns:
        None
    """
    try:
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Content successfully written to {file_name}")
    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")
