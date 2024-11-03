import re


def clean_eos_tokens(content: str) -> str:
    """
    The removal of specific tokens from the content is essential for ensuring that the output
    is clean and free from any artifacts that may interfere with further processing or
    display. These tokens can disrupt the flow of text and may lead to confusion or
    misinterpretation of the generated content. By eliminating them, we enhance the
    readability and usability of the output, making it more suitable for end-user
    applications.
    """
    return re.sub(r"<\|(eot_id|im_end)\|>", "", content)
