import gdb
import sys # Added
from chatgdb import utils
from chatgdb import gdb_explorer # Added import
from chatgdb import multi_stage_processor # Added

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

        def gdb_printer(text_chunk):
            sys.stdout.write(text_chunk)
            sys.stdout.flush()

        # Call the multi-stage processor
        # The multi_stage_processor.generate_gdb_command_multi_stage function
        # will use the gdb_printer callback for any streaming output.
        # It's expected to handle its own newlines for streamed content.
        generated_cmd_to_execute = multi_stage_processor.generate_gdb_command_multi_stage(arg, gdb_printer)
        
        # If the multi-stage processor returns a command, it's already printed (streamed).
        # If it's a stub or has errors, it might print messages via the callback.
        # We might still want a final newline if the callback didn't ensure one.
        if not generated_cmd_to_execute.endswith("\n") and gdb_printer: # Check if callback was used
             sys.stdout.write("\n")
        sys.stdout.flush()


        globals()['prev_command'] = generated_cmd_to_execute # Update prev_command
        
        global chatgdb_ask_mode # Ensure global is used if it's a module-level variable

        # Ask mode logic uses generated_cmd_to_execute
        if generated_cmd_to_execute: # Check if command is not empty
            if chatgdb_ask_mode: 
                try:
                    # The command has already been printed by the streaming callback.
                    response_str = gdb.execute(f'pi print(input("Execute? (y/n): "))', to_string=True)
                    response = response_str.strip().lower().replace('"', '').replace("'", "")
                    if response in ["y", "yes"]:
                        gdb.execute(generated_cmd_to_execute)
                    else:
                        gdb.write("Command not executed.\n")
                except Exception as e:
                    gdb.write(f"Error during confirmation: {e}\n")
                    gdb.write("Command not executed due to error.\n")
            else: # agent mode
                gdb.execute(generated_cmd_to_execute)
        elif not arg == "help": # Don't print error for 'chat help' if it results in empty command
             # The multi-stage processor should have printed an error message via the callback
             # if it failed to generate a command. If it returned empty without printing,
             # this message is a fallback.
             gdb.write("Multi-stage processor did not return a command or an error occurred.\n")


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
        def gdb_explain_printer(text_chunk):
            sys.stdout.write(text_chunk)
            sys.stdout.flush()
        
        # Use globals().get to safely access prev_command
        utils.explain_helper(globals().get('prev_command', ''), arg, EXPLANATION_PROMPT, gdb_explain_printer)
        sys.stdout.write("\n") # Ensure a final newline after streaming
        sys.stdout.flush()


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
        
        def gdb_stop_event_printer(text_chunk):
            # Can't use gdb.write for streaming as it appends newlines.
            # sys.stdout should work in GDB's Python environment.
            sys.stdout.write(text_chunk)
            sys.stdout.flush()

        # get_llm_response now handles streaming via the callback
        # and returns the full response or an "ERROR:" string.
        # The callback handles printing, so no need to print llm_suggestion directly.
        llm_suggestion = utils.get_llm_response(prompt, gdb_stop_event_printer)
        sys.stdout.write("\n") # Ensure a final newline
        sys.stdout.flush()
        
        # If llm_suggestion starts with "ERROR:", make_streaming_request already printed details
        # via the callback and to sys.stderr. Nothing more needed here for that case.
        # The old gdb.write(f"ChatGDB Suggestion: {llm_suggestion}\n") is removed.

    except Exception as e:
        # This will catch errors from within on_gdb_stop itself, 
        # or if get_llm_response (or underlying functions) re-raise an exception
        # not caught by make_streaming_request's error handling.
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
