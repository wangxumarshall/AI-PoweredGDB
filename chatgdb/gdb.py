import gdb
from chatgdb import utils
from chatgdb import gdb_explorer # Added import

prev_command = ""
chatgdb_ask_mode = False # Added global variable
COMMAND_PROMPT = (
    "Based on the user's query, provide a single, precise GDB command. "
    "Consider the typical use cases and syntax for GDB commands. "
    "Ensure the command is directly executable. "
    "Do NOT include any explanation or surrounding text. "
    "User query: "
)
EXPLANATION_PROMPT = "Give me an explanation for this GDB command: "


class GDBCommand(gdb.Command):
    """Custom GDB command - chat

    The chat command is used to generate GDB commands based on plain English
    input.
    """

    def __init__(self):
        """Initializes custom GDB command"""
        super(GDBCommand, self).__init__("chat", gdb.COMMAND_DATA)

    # creates api request on command invocation
    def invoke(self, arg, from_tty):
        """Invokes custom GDB command and sends API request

        Params:
        arg (str): argument passed to command
        from_tty (bool): whether command was invoked from TTY
        """
        global prev_command
        # handling if user is asking for help on how to use the commands
        if arg == "help":
            utils.chat_help()
            return

        prev_command, command = utils.chat_helper(arg, COMMAND_PROMPT)

        global chatgdb_ask_mode
        if chatgdb_ask_mode and command and command.strip():
            try:
                # Using Python's input() as suggested.
                # gdb.write is used to ensure output is through GDB's channels.
                gdb.write(f"Suggested command: {command}\n")
                # We need to execute a python command in GDB to get input this way
                # This is a common pattern for getting user input within GDB scripting
                response_str = gdb.execute('pi print(input("Execute? (y/n): "))', to_string=True)
                # response_str will be something like '"y"\n' or '"n"\n', so we need to clean it.
                response = response_str.strip().lower().replace('"', '') 
                if response in ["y", "yes"]:
                    gdb.execute(command)
                else:
                    gdb.write("Command not executed.\n")
            except Exception as e:
                gdb.write(f"Error during confirmation: {e}\n")
                gdb.write("Command not executed due to error.\n")
        else:
            if command and command.strip(): # Ensure command is not empty
                gdb.execute(command)
            elif not command or not command.strip():
                 gdb.write("ChatGDB received an empty command. Nothing to execute.\n")


class ExplainCommand(gdb.Command):
    """Custom GDB command - explain

    The explain command is used to generate explanations for either the
    previous command or a user query
    """
    def __init__(self):
        """Initializes custom GDB command"""
        super(ExplainCommand, self).__init__("explain", gdb.COMMAND_DATA)

    # creates api request on command invocation
    def invoke(self, arg, from_tty):
        """Invokes custom GDB command and sends API request

        Params:
            arg (str): argument passed to commands
            from_tty (bool): whether command was invoked from from_tty
        """
        utils.explain_helper(prev_command, arg, EXPLANATION_PROMPT)


GDBCommand()
ExplainCommand()

class ChatSetModeCommand(gdb.Command):
    """Custom GDB command - chat-set-mode

    This command allows the user to switch between 'ask' mode (confirm before execution)
    and 'agent' mode (execute directly).
    """
    def __init__(self):
        super(ChatSetModeCommand, self).__init__("chat-set-mode", gdb.COMMAND_SUPPORT, gdb.COMPLETE_SYMBOL)

    def invoke(self, arg, from_tty):
        global chatgdb_ask_mode
        arg = arg.lower().strip()
        if arg == "ask":
            chatgdb_ask_mode = True
            gdb.write("ChatGDB mode set to: Ask\n")
        elif arg == "agent":
            chatgdb_ask_mode = False
            gdb.write("ChatGDB mode set to: Agent\n")
        else:
            gdb.write("Usage: chat-set-mode [ask|agent]\n")

ChatSetModeCommand() # Register the new command

class ChatExploreCommand(gdb.Command):
    def __init__(self):
        super(ChatExploreCommand, self).__init__("chat-explore", gdb.COMMAND_DATA, gdb.COMPLETE_SYMBOL)
        # COMPLETE_SYMBOL allows for symbol completion for arguments, which might be useful.

    def invoke(self, arg, from_tty):
        if not arg:
            gdb.write("Usage: chat-explore <your query or initial variable/command to explore>\n")
            return
        
        # Directly call gdb_explorer.explore_state.
        # explore_state will use gdb.execute and gdb.write directly.
        gdb_explorer.explore_state(arg)

ChatExploreCommand() # Register the new explore command

def on_gdb_stop(event):
    # Check if the stop event is something we want to react to.
    # For example, avoid reacting to temporary internal stops if possible.
    # gdb.StopEvent has attributes like 'stop_signal'.
    # A simple check for now: ensure there's a selected frame.
    if not gdb.selected_frame().is_valid():
        return

    gdb.write("\n--- ChatGDB Contextual Assistance ---\n")
    try:
        current_frame = gdb.selected_frame()
        frame_info_parts = []
        if current_frame.name():
            frame_info_parts.append(f"Function: {current_frame.name()}")
        if current_frame.pc():
             frame_info_parts.append(f"PC: {current_frame.pc()}")
        try: # Source and line can fail if no debug symbols
            sal = current_frame.find_sal()
            if sal.symtab:
                frame_info_parts.append(f"File: {sal.symtab.filename}")
            if sal.line:
                frame_info_parts.append(f"Line: {sal.line}")
        except gdb.error:
            frame_info_parts.append("Source/line info not available.")

        frame_info = "Stopped at: " + ", ".join(frame_info_parts) + "\n"
        
        locals_str = ""
        try:
            locals_output = gdb.execute("info locals", to_string=True)
            if locals_output and locals_output.strip() and "No locals." not in locals_output:
               locals_str = f"Locals:\n{locals_output.strip()}\n"
            else:
               locals_str = "Locals: No locals found or info locals failed.\n"
        except Exception as e:
            locals_str = f"Error fetching locals: {str(e)}\n"

        args_str = ""
        try:
            args_output = gdb.execute("info args", to_string=True)
            if args_output and args_output.strip() and "No arguments." not in args_output:
                args_str = f"Arguments:\n{args_output.strip()}\n"
            else:
                args_str = "Arguments: No arguments found or info args failed.\n"
        except Exception as e:
            args_str = f"Error fetching arguments: {str(e)}\n"

        context_summary = frame_info + args_str + locals_str
        gdb.write(context_summary)

        prompt = (
            f"GDB has stopped. Here's the current context:\n{context_summary}\n"
            "What are 1-2 brief, general suggestions or common next debugging steps a developer might take based on this? "
            "Focus on actionable GDB commands or areas to investigate. Example: 'Consider `step` / `next`. Examine variable X if its value seems off.'"
        )
        
        llm_suggestion = utils.get_llm_response(prompt) 
        gdb.write(f"ChatGDB Suggestion: {llm_suggestion}\n")

    except Exception as e:
        gdb.write(f"Error in ChatGDB context assistance: {str(e)}\n")
    finally:
        gdb.write("--- End Contextual Assistance ---\n")

# Register the event handler
gdb.events.stop.connect(on_gdb_stop)

def main():
    print("ChatGDB loaded successfully. Type 'chat help' for information "
          "on how to run the commands.")


if __name__ == "__main__":
    main()
