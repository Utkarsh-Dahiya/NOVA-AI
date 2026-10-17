import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI


# Load environment variables from the project's .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Give clear, accurate, and beginner-friendly answers."
)


# Available AI providers
PROVIDERS = {
    "1": {
        "name": "Groq",
        "env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-20b",
        "class": ChatGroq,
    },
    "2": {
        "name": "Google Gemini",
        "env": "GOOGLE_API_KEY",
        # Change this if the model is unavailable to your account.
        "model": "gemini-3.8-flash",
        "class": ChatGoogleGenerativeAI,
    },
    "3": {
        "name": "OpenAI",
        "env": "OPENAI_API_KEY",
        "model": "gpt-4.1-mini",
        "class": ChatOpenAI,
    },
    "4": {
        "name": "Mistral",
        "env": "MISTRAL_API_KEY",
        "model": "mistral-small-latest",
        "class": ChatMistralAI,
    },
}


def create_model(provider):
    """Create the selected AI model using its API key."""

    api_key = os.getenv(provider["env"])

    if not api_key:
        raise ValueError(
            f"{provider['env']} is missing from your .env file."
        )

    model_class = provider["class"]

    return model_class(
        model=provider["model"],
        temperature=0.7,
        api_key=api_key,
    )


def print_menu():
    """Display the provider selection menu."""

    print("\n" + "=" * 45)
    print("         MULTI-MODEL AI CHATBOT")
    print("=" * 45)

    for option, provider in PROVIDERS.items():
        print(f"{option}. {provider['name']}")

    print("5. Exit")
    print("=" * 45)


def chat_with_model(model, provider_name):
    """Run a conversation with the selected AI model."""

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    print(f"\nConnected to {provider_name}!")
    print("Type 'back' to choose another provider.")
    print("Type 'exit' to close the application.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "back":
                print("\nReturning to the main menu...")
                return True

            if user_input.lower() == "exit":
                return False

            messages.append(HumanMessage(content=user_input))

            response = model.invoke(messages)

            answer = response.content

            # Handle text and other content blocks safely.
            if isinstance(answer, list):
                answer = "\n".join(
                    block.get("text", str(block))
                    if isinstance(block, dict)
                    else str(block)
                    for block in answer
                )

            print(f"\nAI ({provider_name}): {answer}\n")

            messages.append(response)

        except KeyboardInterrupt:
            print("\n\nReturning to the main menu...")
            return True

        except Exception as error:
            # Remove the failed user message so it is not resent
            # as part of the conversation history.
            if messages and isinstance(messages[-1], HumanMessage):
                messages.pop()

            print(f"\nError: {error}")
            print(
                "Check your API key, model availability, "
                "internet connection, and provider quota.\n"
            )


def main():
    """Application entry point."""

    print("\nWelcome to your Multi-Model AI Chatbot!")

    while True:
        print_menu()
        choice = input("Choose an option (1-5): ").strip()

        if choice == "5":
            print("\nThanks for using the chatbot. Goodbye!")
            break

        if choice not in PROVIDERS:
            print("\nInvalid choice. Please enter a number from 1 to 5.")
            continue

        provider = PROVIDERS[choice]

        try:
            model = create_model(provider)

            should_continue = chat_with_model(
                model,
                provider["name"],
            )

            if not should_continue:
                print("\nThanks for using the chatbot. Goodbye!")
                break

        except ValueError as error:
            print(f"\nConfiguration error: {error}")
            print("Add the required API key to your .env file.")

        except Exception as error:
            print(f"\nCould not initialize {provider['name']}.")
            print(f"Details: {error}")
            print(
                "Verify the API key, account access, model name, "
                "and provider quota."
            )


if __name__ == "__main__":
    main()