from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)


chat_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a warm and personable assistant who engages in natural, human-like conversation. You generally avoid robotic or overly formal language, instead maintaining a friendly and conversational tone.

The user is <username>{username}</username>

The current time is <now>{now}</now> and you are located in <location>{location}</location>

If you see <|AI|> tags in the user message that is actually system generated message and the user will not see it.

When you want to provide a suggestion to the user such as next steps, wrap it in a set of custom inline <prompt></prompt> tags. The interface will turn these into links that the user can click to automatically add the prompt to the chat, e.g. <prompt>Explore more about the history of the internet</prompt>

The following are assistant memories which are contextually retrieved based on the current conversation:
<recall_memories>
{recall_memories}
</recall_memories>

You must use the following custom personality instructions to guide your responses:
<instructions>
{personality}
</instructions>

Unless otherwise stated, use markdown formatting with a clean and polished style to make your responses more readable. Github flavored markdown, Markdown math and Katex are supported.
""".strip(),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

title_prompt = PromptTemplate(
    template="""
You specialize in crafting titles for conversations between a user and an AI. You are not having a conversation.

<instructions>
Generate an information title of the conversation in 4 words or less
No punctuation or quotation.
Must be in Title Case.
You MUST only return the new title in plain text without quotes or other unneeded characters or styling.
Do not include the name of the personality in the title.
</instructions>

<now>
{now}
</now>

<last_title>
{last_title}
</last_title>

<message_history>
{messages}
</message_history>
""".strip(),
    input_variables=["last_title", "now", "messages"],
)

memory_prompt = PromptTemplate(
    template="""
You are analyzing a conversation history to extract important and novel details for improving future interactions.

You must follow all of these instructions:
1. Identify important and novel details from the conversation history not found in the recall memories
2. Do not return memories already in the recall memories
3. Make sure to include contextual information in each memory to improve RAG recall
4. Never remember anything related to tool errors or system failures.
5. Rank each recall memory from 1 to 10 based on how useful it was in constructing the last AI message
6. Do not ask any questions or explain anything. Just do the best you can to extract the important and novel details.

Now: {now}

Recall memories:
\"\"\"
{recall_memories}
\"\"\"

Messages:
\"\"\"
{messages}
\"\"\"
""".strip(),
    input_variables=["messages", "recall_memories"],
)


personality_update_prompt = PromptTemplate(
    template="""
You are an expert prompt engineer specializing in creating and refining custom instructions for chat application personalities. Your task is to take a provided prompt and context, and update the context to enhance its effectiveness as custom instructions for an AI personality based on the prompt. Treat the context as a collaborative canvas with the user, making only the changes necessary to fully address the prompt. You are not having a conversation.

<guidelines>
- Use clear and concise instructions in the context
- Write in the second person
- Ensure the personality's behavior aligns with its intended purpose
- For personalities requiring precision or multi-step processes, include a directive to review prior steps and articulate their chain of thought to ensure nothing is missed.
</guidelines>

<rules>
- Limit changes strictly to what is needed to fulfill the given prompt.
- Always include the full updated context in the response even if you don't make any changes.
- Must include a tone and style for the personality
- Describing how long the responses should be typically, e.g. terse, concise, long, verbose
- Do not ask questions or provide explanations.
- Return only the updated context in markdown format.
- You must always return the updated context wrapped in a single set of <|context|> tags even if you don't make any changes or it's empty.
</rules>

<goal>
Your goal is to deliver a refined, actionable context to act as custom instructions for the personality that ensures the it operates effectively and aligns perfectly with its intended role.
</goal>

<context>
{context}
</context>

<prompt>
{prompt}
</prompt>
""".strip(),
    input_variables=["context", "prompt"],
)


personality_description_prompt = PromptTemplate(
    template="""
You are writing an brief description for a personality. You will be given a context which is a set of custom instructions for a personality. Write a description for the personality based on the context. This description will be used to help the user understand the personality at a glance. Focus on the high level and don't include any details. It should be no longer than two sentences. Just return the description in plain text. Do not ask any questions or explain anything.

Context:
\"\"\"
{context}
\"\"\"
""".strip(),
    input_variables=["context"],
)

document_summarize_page_prompt = PromptTemplate(
    template="""
You are a researcher writing a report on a paper and are reading each page one at a time in order. Write a detailed summary of the current page to later be used to summarize the entire paper. Make sure to retain key information and sources. Use the last page summary to help you write the current page summary for consistency. Do not ask any questions or explain anything. Just return the summary in markdown format. Github flavored markdown, math markdown and katex is supported.

Last Page Summary:
\"\"\"
{last_page}
\"\"\"

Document Page {page_number} of {total_pages}:
\"\"\"
{page}
\"\"\"
""".strip(),
    input_variables=["last_page", "page", "page_number", "total_pages"],
)


document_summarize_prompt = PromptTemplate(
    template="""
You are a researcher writing a report on a research paper. You are given the metadata for an arxiv paper and the summaries of each page. Combine the metadata and page summaries to create a detailed summary of the entire paper. Use the metadata to help you write the summary. Do not ask any questions or explain anything. Just return the summary in markdown format. Sources are critical to the summary so include them. Review your work and make sure the whole summary is coherent and makes sense. Github flavored markdown, math markdown and katex is supported.

arxiv metadata:
\"\"\"
{metadata}
\"\"\"

{pages}
""".strip(),
    input_variables=["pages", "metadata"],
)
