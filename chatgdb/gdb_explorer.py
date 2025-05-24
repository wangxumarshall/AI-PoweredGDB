import gdb
import json # Ensure json is imported
import sys # Added
from chatgdb import utils # Assuming utils.py contains get_model, get_key, etc.

def _explorer_printer(text_chunk):
    # Using sys.stdout for direct printing in GDB context, as gdb.write adds newlines
    sys.stdout.write(text_chunk)
    sys.stdout.flush()

# Placeholder for initial command generation - can be improved later
def _generate_initial_command(query):
    # Construct a prompt to ask the LLM for the best initial GDB command.
    initial_command_prompt = (
        f"The user wants to start a debugging exploration related to the query: '{query}'. "
        "Based on this query, what single, directly executable GDB command is the best first step to investigate? "
        "Respond with ONLY the GDB command itself, without any explanation, preceding text, or surrounding quotes/markdown."
    )
    
    # Call the LLM to get the suggested initial command.
    # utils.get_llm_response is assumed to handle the API call and return the text response.
    # The callback will handle printing the streamed response.
    sys.stdout.write("ChatGDB Explorer (Initial Command Suggestion): ") # Prefix for clarity
    sys.stdout.flush()
    suggested_command = utils.get_llm_response(initial_command_prompt, _explorer_printer)
    sys.stdout.write("\n") # Ensure a final newline after streaming
    sys.stdout.flush()
    
    # Basic cleaning: remove potential quotes if LLM wraps output, though prompt tries to prevent this.
    if suggested_command.startswith('"') and suggested_command.endswith('"'):
        suggested_command = suggested_command[1:-1]
    if suggested_command.startswith("'") and suggested_command.endswith("'"):
        suggested_command = suggested_command[1:-1]
        
    return suggested_command.strip()

def explore_state(initial_query, max_iterations=3):
    gdb.write(f"Starting exploration for: {initial_query}\n")
    history = [] 
    # current_llm_input_command will store the raw suggestion from LLM for the next command
    # It's initialized to empty, so the first command comes from _generate_initial_command
    current_llm_input_command = "" 

    for i in range(max_iterations):
        gdb.write(f"--- Exploration Step {i+1}/{max_iterations} ---\n")

        if i == 0:
            gdb_command_to_run = _generate_initial_command(initial_query)
        else:
            # current_llm_input_command holds the raw suggestion from previous iteration
            # If it was a HYPOTHESIS or DONE, we would have broken already.
            # So, if it's not empty, it should be a command.
            if not current_llm_input_command:
                gdb.write("LLM did not suggest a command in the previous step. Ending exploration.\n")
                break
            # Check if the suggestion itself is a terminal state (should have been caught below, but as safety)
            if current_llm_input_command.startswith("HYPOTHESIS:") or \
               current_llm_input_command.startswith("DONE:"):
                gdb.write("Previous LLM response was a terminal state. Ending exploration.\n")
                break
            gdb_command_to_run = current_llm_input_command

        gdb.write(f"Executing: {gdb_command_to_run}\n")
        try:
            command_output = gdb.execute(gdb_command_to_run, to_string=True)
            if command_output is None: command_output = "<no output>"
            # Strip trailing newlines that gdb.execute might add, but keep internal ones
            command_output = command_output.rstrip('\n') 
            gdb.write(f"Output:\n{command_output}\n")
        except Exception as e:
            command_output = f"Error executing command '{gdb_command_to_run}': {str(e)}"
            gdb.write(f"{command_output}\n")
            history.append((gdb_command_to_run, command_output))
            # As per instructions, if an error occurs, print error and break.
            # Future improvement: let LLM try to recover.
            gdb.write("Error encountered during command execution. Ending exploration.\n")
            break 
         
        history.append((gdb_command_to_run, command_output))

        history_str = "\n".join([f"Cmd: {h[0]}\nOut: {h[1]}" for h in history])
        
        prompt_for_llm = (
            f"User's initial debug query: '{initial_query}'.\n"
            f"Debugging history so far (last executed command was '{gdb_command_to_run}'):\n{history_str}\n\n"
            "Based on this history and the initial query, what is the single BEST next GDB command to execute to investigate further? "
            "Or, if you have a strong hypothesis, state it prefixed with 'HYPOTHESIS: '. "
            "If no more useful commands can be run or the issue is likely found, state 'DONE: ' followed by a summary. "
            "If suggesting a GDB command, provide ONLY the command itself, without any additional explanation or formatting. "
            "If the previous command resulted in an error, consider what might have caused it (e.g., invalid syntax, non-existent variable) and suggest a corrected command or a different approach."
        )

        sys.stdout.write("ChatGDB Explorer (Next Step Suggestion): ") # Prefix for clarity
        sys.stdout.flush()
        llm_suggestion = utils.get_llm_response(prompt_for_llm, _explorer_printer)
        sys.stdout.write("\n") # Ensure a final newline
        sys.stdout.flush()
        
        # current_llm_input_command will hold the fully assembled response.
        # If it starts with "ERROR:", make_streaming_request already printed details.
        current_llm_input_command = llm_suggestion.strip() 

        if current_llm_input_command.startswith("HYPOTHESIS:"):
            gdb.write(f"LLM Hypothesis: {current_llm_input_command[len('HYPOTHESIS:').:].strip()}\n")
            break 
        if current_llm_input_command.startswith("DONE:"):
            gdb.write(f"LLM Conclusion: {current_llm_input_command[len('DONE:').:].strip()}\n")
            break
        
        # If it's neither HYPOTHESIS, DONE, nor an empty string, it's assumed to be the next command.
        if not current_llm_input_command:
             gdb.write("LLM returned an empty suggestion. Ending exploration.\n")
             break

        if i == max_iterations - 1:
            gdb.write("Max iterations reached. Ending exploration.\n")

    gdb.write("--- Exploration Finished ---\n")
