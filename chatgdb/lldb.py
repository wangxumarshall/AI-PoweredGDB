import lldb
from chatgdb import utils


def __lldb_init_module(debugger, internal_dict):
    """This function handles the initialization of the custom commands"""
    # lldb doesn't trigger python's main function so we print the help here
    print("ChatLLDB loaded successfully. Type 'chat help' for information "
          "on how to run the commands.")
    debugger.HandleCommand('command script add -f lldb.chat chat')
    debugger.HandleCommand('command script add -f lldb.explain explain')
    debugger.HandleCommand('command script add -f lldb.chat_set_mode chat-set-mode') # Register new command


prev_command = ""
chatgdb_ask_mode = False # Added global variable
COMMAND_PROMPT = (
    "Based on the user's query, provide a single, precise LLDB command. "
    "Do NOT provide a GDB command. "
    "Consider the typical use cases and syntax for LLDB commands. "
    "Ensure the command is directly executable. "
    "Do NOT include any explanation or surrounding text. "
    "User query: "
)
EXPLANATION_PROMPT = "Give me an explanation for this LLDB command: "


def chat(debugger, command, result, internal_dict):
    """Custom LLDB command - chat

    The chat command is used to generate GDB commands based on plain English
    input.
    """
    global prev_command
    # handle when user types 'chat help'
    if command == "help":
        utils.chat_help()
        return

    prev_command, generated_command_str = utils.chat_helper(command, prompt=COMMAND_PROMPT)

    global chatgdb_ask_mode
    if chatgdb_ask_mode and generated_command_str and generated_command_str.strip():
        result.PutStr(f"Suggested command: {generated_command_str}\n")
        
        # Using lldb.debugger.GetCommandInterpreter().HandleCommand() for input
        input_script_command = f'script print(input("Execute? (y/n): ").lower().strip())'
        return_obj = lldb.SBCommandReturnObject()
        lldb.debugger.GetCommandInterpreter().HandleCommand(input_script_command, return_obj)
        
        response = ""
        if return_obj.Succeeded():
            # Clean up output, removing potential quotes and newlines
            response = return_obj.GetOutput().strip().replace('"', '').replace("'", "").replace("\\n", "")
        else:
            result.PutStr("Error getting user input. Defaulting to no execution.\n")
            response = "n" # Default to no if input fails

        if response in ["y", "yes"]:
            debugger.HandleCommand(generated_command_str)
        else:
            result.PutStr("Command not executed.\n")
    else:
        if generated_command_str and generated_command_str.strip(): # Ensure command is not empty
            debugger.HandleCommand(generated_command_str)
        elif not generated_command_str or not generated_command_str.strip():
            result.PutStr("ChatLLDB received an empty command. Nothing to execute.\n")


def explain(debugger, command, result, internal_dict):
    """Custom LLDB command - explain

    The explain command is used to generate explanations for either the
    previous command or a user query
    """
    utils.explain_helper(prev_command, command, prompt=EXPLANATION_PROMPT)


def chat_set_mode(debugger, command_args_str, result, internal_dict):
    """Custom LLDB command - chat-set-mode

    This command allows the user to switch between 'ask' mode (confirm before execution)
    and 'agent' mode (execute directly).
    """
    global chatgdb_ask_mode
    args = command_args_str.lower().strip()
    if args == "ask":
        chatgdb_ask_mode = True
        result.PutStr("ChatLLDB mode set to: Ask\n")
    elif args == "agent":
        chatgdb_ask_mode = False
        result.PutStr("ChatLLDB mode set to: Agent\n")
    else:
        result.PutStr("Usage: chat-set-mode [ask|agent]\n")
