import lldb
import sys # Added
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

    def lldb_printer(text_chunk):
        # 'result' is SBCommandReturnObject, use sys.stdout for direct streaming
        sys.stdout.write(text_chunk)
        sys.stdout.flush()
    
    # global prev_command # Ensure this is declared if prev_command is module-level
    # The chat_helper returns (full_assembled_command, full_assembled_command)
    _discarded_prev_cmd, generated_cmd_to_execute = utils.chat_helper(command, prompt=COMMAND_PROMPT, print_callback=lldb_printer)
    sys.stdout.write("\n") # Ensure a final newline
    sys.stdout.flush()
    
    globals()['prev_command'] = generated_cmd_to_execute
    
    global chatgdb_ask_mode # Ensure global is used

    if generated_cmd_to_execute: # Check if command is not empty
        if chatgdb_ask_mode: 
            # LLDB's input mechanism:
            # The suggested command is already printed by the streaming callback.
            # We need to prompt for y/n.
            input_script_command = f'script print(input("Execute? (y/n): ").lower().strip())'
            return_obj = lldb.SBCommandReturnObject()
            lldb.debugger.GetCommandInterpreter().HandleCommand(input_script_command, return_obj)
            response = "n" # Default to no
            if return_obj.Succeeded():
                response = return_obj.GetOutput().strip().replace("\n", "").replace("'", "").replace('"', '')
            
            if response in ["y", "yes"]:
                debugger.HandleCommand(generated_cmd_to_execute)
            else:
                result.PutStr("Command not executed.\n") # Use result for feedback in LLDB
        else: # agent mode
            debugger.HandleCommand(generated_cmd_to_execute)
    elif command != "help": # Don't print error for 'chat help' if it results in empty command
         result.PutStr("LLM did not return a command or an error occurred.\n")


def explain(debugger, command, result, internal_dict):
    """Custom LLDB command - explain

    The explain command is used to generate explanations for either the
    previous command or a user query
    """
    def lldb_explain_printer(text_chunk):
        sys.stdout.write(text_chunk)
        sys.stdout.flush()

    # Use globals().get to safely access prev_command
    utils.explain_helper(globals().get('prev_command', ''), command, EXPLANATION_PROMPT, lldb_explain_printer)
    sys.stdout.write("\n") # Ensure a final newline
    sys.stdout.flush()


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
