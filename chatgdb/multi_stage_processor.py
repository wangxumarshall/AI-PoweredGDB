import gdb
import os
import sys
from chatgdb import utils # For get_llm_response

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompts")
PROMPTS = {
    "stage1": None,
    "stage3": None,
    "stage5": None
}

SUPPORTED_COMMAND_CLASSES = [
    "breakpoints", "data", "files", "internals", "obscure", "running",
    "stack", "status", "support", "text-user-interface", "tracepoints", "user-defined"
]

# Flag to ensure prompts are loaded only once or if loading failed previously
_prompts_loaded_successfully = False

def load_prompts():
    global _prompts_loaded_successfully
    if _prompts_loaded_successfully: # Don't reload if already successful
        return True
    
    required_prompts = ["stage1", "stage3", "stage5"]
    all_found = True
    for stage_name in required_prompts:
        # Corrected filenames based on earlier convention, assuming they are:
        # stage1_classify.md, stage3_select_command.md, stage5_generate_final_command.md
        # The user provided just stage1_classify.md, stage3_select_command.md, stage5_generate_final_command.md. Let's use those.
        actual_filename = f"{stage_name}.md" # This matches the file creation step more directly.
        if stage_name == "stage1": actual_filename = "stage1_classify.md"
        elif stage_name == "stage3": actual_filename = "stage3_select_command.md"
        elif stage_name == "stage5": actual_filename = "stage5_generate_final_command.md"

        filepath = os.path.join(PROMPT_DIR, actual_filename)
        try:
            with open(filepath, "r") as f:
                PROMPTS[stage_name] = f.read()
        except FileNotFoundError:
            sys.stderr.write(f"[MultiStageProcessor] Error: Prompt file not found: {filepath}\n")
            all_found = False
            break # Stop if any prompt is missing
        except IOError as e:
            sys.stderr.write(f"[MultiStageProcessor] Error reading prompt file {filepath}: {e}\n")
            all_found = False
            break
    
    if all_found:
        _prompts_loaded_successfully = True
        return True
    else:
        # Ensure prompts are None if loading failed to prevent partial use
        for stage_name in required_prompts:
            PROMPTS[stage_name] = None
        _prompts_loaded_successfully = False
        return False

def generate_gdb_command_multi_stage(user_query, print_callback):
    if not _prompts_loaded_successfully: # Try loading if not already successful
        if not load_prompts():
            if print_callback: # Check if callback is None
                print_callback("[MultiStageProcessor] Error: Could not load system prompts. Aborting multi-stage processing.\n")
            else: # Fallback if no callback provided, though it should be
                sys.stderr.write("[MultiStageProcessor] Error: Could not load system prompts and no print_callback provided.\n")
            return "" # Return empty for error

    # Placeholder for actual multi-stage logic
    if print_callback:
        print_callback(f"[MultiStageProcessor] STUB: Received query: '{user_query}'. Multi-stage logic not yet implemented.\n")
    
    # For now, return a simple echo command or an empty string if it's safer
    # return f"echo 'Multi-stage processing for "{user_query}" is a STUB'"
    # return "" # Returning empty might be safer until fully implemented

    # --- Stage 1: Classify User Request ---
    if print_callback:
        print_callback("--- Stage 1: Classifying user intent ---\n")
    
    # PROMPTS["stage1"] from file should end with "User Query:
" # Note: The prompt files actually don't end with this.
    # The user_query will be appended directly.
    stage1_full_prompt = PROMPTS["stage1"] + user_query 
    
    llm_response_stage1_raw = utils.get_llm_response(stage1_full_prompt, print_callback)
    if print_callback: 
        print_callback("\n") # Newline after raw LLM stream for this stage

    if not llm_response_stage1_raw or llm_response_stage1_raw.startswith("ERROR:"):
        if print_callback:
            # Error message from get_llm_response (via make_streaming_request) is already printed by the callback.
            # So, just indicate the stage.
            print_callback(f"[MultiStageProcessor] Error in Stage 1 LLM call.\n")
        return ""

    command_class, summary, error_msg = _parse_stage1_response(llm_response_stage1_raw)

    if error_msg and command_class is None : # If command_class is None, it's a fatal parsing error
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 1 Error: {error_msg}. Raw response: '{llm_response_stage1_raw}'\n")
        return ""
    
    # If error_msg is just a warning (e.g., LLM returned 1 line), command_class might still be valid.
    if error_msg and print_callback: # Print warnings if any
            print_callback(f"[MultiStageProcessor] Stage 1 Info: {error_msg}\n")

    if command_class is None: # Should be caught by previous check, but as a safeguard
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 1 Error: Failed to determine command class. Raw response: '{llm_response_stage1_raw}'\n")
        return ""

    if command_class not in SUPPORTED_COMMAND_CLASSES:
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 1 Error: LLM provided an invalid command class: '{command_class}'. Expected one of: {', '.join(SUPPORTED_COMMAND_CLASSES)}.\nRaw response: '{llm_response_stage1_raw}'\n")
        return ""

    if print_callback:
        print_callback(f"[MultiStageProcessor] Stage 1 Summary: '{summary}'\n")
        print_callback(f"[MultiStageProcessor] Stage 1 Result: Determined command class: '{command_class}'\n")

    # Placeholder for subsequent stages
    # return f"echo 'Stage 1 Done. Class: {command_class}. Summary: {summary}. Next: Implement Stage 2 (Get GDB Help)'"

    # --- Stage 2: Get GDB Help for Command Class & Filter ---
    if print_callback:
        print_callback(f"--- Stage 2: Getting GDB help for class '{command_class}' ---\n")

    gdb_help_command = f"help {command_class}"
    # Pass print_callback to _execute_gdb_command_safely so it can also stream GDB's own command echo if desired (though it's simple here)
    help_class_output = _execute_gdb_command_safely(gdb_help_command, to_string=True, print_callback=print_callback)

    if help_class_output.startswith("GDB_EXECUTION_ERROR:") or help_class_output.startswith("PYTHON_EXECUTION_ERROR:"):
        if print_callback:
            # Error already printed by _execute_gdb_command_safely via print_callback
            # (or directly if print_callback was None, though not in this flow)
            print_callback(f"[MultiStageProcessor] Stage 2 Error: Failed to get help for class '{command_class}'.\n")
        return "" # Stop processing

    # Stage 2.1: Filter help_class_output
    list_of_commands_marker = "List of commands:" # AgentGDB uses "List of commands:"
    marker_pos = help_class_output.find(list_of_commands_marker)

    if marker_pos == -1:
        # Fallback: some GDB versions/outputs might use "Command class "classes" contains the following commands:"
        list_of_commands_marker_alt = f"Command class \"{command_class}\" contains the following commands:"
        marker_pos = help_class_output.find(list_of_commands_marker_alt)
        if marker_pos != -1:
            list_of_commands_marker = list_of_commands_marker_alt # Use the found marker
        else: # Neither marker found
            if print_callback:
                print_callback(f"[MultiStageProcessor] Stage 2.1 Error: Could not find start-of-commands marker in help output for '{command_class}'. Output was:\n{help_class_output}\n")
            return ""
    
    # Take text after the marker
    gdb_cmd_class_help_filtered = help_class_output[marker_pos + len(list_of_commands_marker):]
    
    # Filter out lines starting with "set " (as AgentGDB does)
    lines = gdb_cmd_class_help_filtered.split('\n')
    filtered_lines = [line for line in lines if not line.strip().startswith("set ")]
    gdb_cmd_class_help_filtered = '\n'.join(filtered_lines).strip()

    if not gdb_cmd_class_help_filtered:
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 2.1 Error: No commands found for class '{command_class}' after filtering, or all commands started with 'set '.\nOriginal help output (after marker):\n{help_class_output[marker_pos + len(list_of_commands_marker):]}\n")
        return ""

    if print_callback:
        # Print a snippet of the filtered help for context, not the whole thing if it's huge.
        snippet = (gdb_cmd_class_help_filtered[:200] + '...') if len(gdb_cmd_class_help_filtered) > 200 else gdb_cmd_class_help_filtered
        print_callback(f"[MultiStageProcessor] Stage 2 Result: Filtered help for '{command_class}':\n{snippet}\n")

    # Placeholder for subsequent stages
    # return f"echo 'Stage 2 Done. Filtered help for {command_class} obtained. Next: Implement Stage 3 (Select specific command)'"

    # --- Stage 3: Select the Most Relevant GDB Command ---
    if print_callback:
        print_callback(f"--- Stage 3: Selecting specific command from class '{command_class}' ---\n")

    # PROMPTS["stage3"] ends with "List of commands:
" (as per prompt file content)
    # We append the filtered help, then the user query.
    stage3_full_prompt = PROMPTS["stage3"] + gdb_cmd_class_help_filtered + "\nUser Query: " + user_query
    
    # utils.get_llm_response will use print_callback for streaming
    llm_response_stage3_raw = utils.get_llm_response(stage3_full_prompt, print_callback)
    if print_callback:
        print_callback("\n") # Newline after raw LLM stream for this stage

    if not llm_response_stage3_raw or llm_response_stage3_raw.startswith("ERROR:"):
        if print_callback:
            # Error message from get_llm_response (via make_streaming_request) is already printed by the callback.
            print_callback(f"[MultiStageProcessor] Error in Stage 3 LLM call.\n") # llm_response_stage3_raw may contain the error details.
        return ""

    selected_command_name = _parse_llm_response_for_last_line(llm_response_stage3_raw)

    if not selected_command_name:
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 3 Error: LLM did not select a specific command from the list for class '{command_class}'. Or the response was empty after parsing.\nRaw LLM response for selection: '{llm_response_stage3_raw}'\n")
        return ""
        
    # Optional: Could try to validate selected_command_name against commands in gdb_cmd_class_help_filtered
    # For now, we trust the LLM's selection if it's non-empty.

    if print_callback:
        print_callback(f"[MultiStageProcessor] Stage 3 Result: Selected command: '{selected_command_name}'\n")

    # Placeholder for subsequent stages
    # return f"echo 'Stage 3 Done. Selected command: {selected_command_name}. Next: Implement Stage 4 (Get Detailed Help)'"

    # --- Stage 4: Get GDB Detailed Help for Selected Command ---
    if print_callback:
        print_callback(f"--- Stage 4: Getting detailed GDB help for command '{selected_command_name}' ---\n")

    gdb_detailed_help_command = f"help {selected_command_name}"
    # Pass print_callback to _execute_gdb_command_safely so it can show GDB's command execution
    detailed_help_output = _execute_gdb_command_safely(gdb_detailed_help_command, to_string=True, print_callback=print_callback)

    if detailed_help_output.startswith("GDB_EXECUTION_ERROR:") or detailed_help_output.startswith("PYTHON_EXECUTION_ERROR:"):
        if print_callback:
            # Error message already printed by _execute_gdb_command_safely via print_callback
            print_callback(f"[MultiStageProcessor] Stage 4 Error: Failed to get detailed help for command '{selected_command_name}'.\n")
        return "" # Stop processing
    
    if not detailed_help_output.strip():
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 4 Warning: Received empty detailed help output for command '{selected_command_name}'. Proceeding, but Stage 5 might be affected.\n")
        # Not returning "" here, as an empty help string might still be processable by Stage 5,
        # or Stage 5 might decide there's no valid command.

    if print_callback:
        # Print a snippet of the detailed help for context
        snippet = (detailed_help_output[:300] + '...') if len(detailed_help_output) > 300 else detailed_help_output
        print_callback(f"[MultiStageProcessor] Stage 4 Result: Detailed help for '{selected_command_name}':\n{snippet}\n")

    # Placeholder for subsequent stage
    # Store detailed_help_output for Stage 5. It will be passed implicitly if generate_gdb_command_multi_stage is one large function.
    # For the subtask, the return string demonstrates it's available.
    # return f"echo 'Stage 4 Done. Detailed help for {selected_command_name} obtained. Next: Implement Stage 5 (Generate Final Command)'"

    # --- Stage 5: Generate Final GDB Command(s) ---
    if print_callback:
        print_callback(f"--- Stage 5: Generating final GDB command(s) based on help for '{selected_command_name}' ---\n")

    # PROMPTS["stage5"] (from stage5_generate_final_command.md) ends with "Help Query: 
"
    # We append detailed_help_output, then "User Query: ", then the user_query.
    stage5_full_prompt = PROMPTS["stage5"] + detailed_help_output + "\nUser Query: " + user_query
    
    llm_response_stage5_raw = utils.get_llm_response(stage5_full_prompt, print_callback)
    if print_callback:
        print_callback("\n") # Newline after raw LLM stream

    if not llm_response_stage5_raw or llm_response_stage5_raw.startswith("ERROR:"):
        if print_callback:
            print_callback(f"[MultiStageProcessor] Error in Stage 5 LLM call: {llm_response_stage5_raw}\n")
        return ""

    final_gdb_command = llm_response_stage5_raw.strip()

    if not final_gdb_command:
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 5 Error: LLM returned an empty response for the final command.\n")
        return ""

    if final_gdb_command == "# No valid command":
        if print_callback:
            print_callback(f"[MultiStageProcessor] Stage 5 Info: LLM determined no valid command could be formed based on the provided help and query.\n")
        return "" # Return empty, indicating no command to execute

    if print_callback:
        print_callback(f"[MultiStageProcessor] Stage 5 Result: Final GDB Command(s):\n{final_gdb_command}\n")

    return final_gdb_command # Return the actual GDB command string(s)

def _parse_llm_response_for_last_line(response_text):
    if not response_text: # Handles None or empty string
        return "" 
    lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]
    if not lines:
        return "" 
    return lines[-1]

def _execute_gdb_command_safely(command_str, to_string=False, print_callback=None):
    """
    Executes a GDB command and handles potential errors.
    Returns the command output or an error-prefixed string.
    """
    if print_callback:
        print_callback(f"[MultiStageProcessor] Executing GDB command: {command_str}\n")
    try:
        output = gdb.execute(command_str, to_string=to_string)
        if to_string and output is None: # Some commands return None on success instead of empty string
            return ""
        return output if to_string else "" # Don't return the gdb.Value object if not to_string
    except gdb.error as e: # Errors during GDB command execution (e.g., command not found, syntax error)
        err_msg = f"GDB_EXECUTION_ERROR: Error executing GDB command '{command_str}': {str(e)}"
        if print_callback:
            print_callback(f"[MultiStageProcessor] {err_msg}\n")
        return err_msg
    except Exception as e: # Other Python errors during the gdb.execute call
        err_msg = f"PYTHON_EXECUTION_ERROR: Python error during GDB command '{command_str}': {str(e)}"
        if print_callback:
            print_callback(f"[MultiStageProcessor] {err_msg}\n")
        return err_msg

def _parse_stage1_response(response_text):
    lines = [line.strip() for line in response_text.strip().split('\n') if line.strip()]
    if len(lines) >= 2:
        # Per AgentGDB: summary is second to last, command class is the last line.
        # This handles potential <think> blocks or other multi-line preamble from the LLM.
        command_class = lines[-1]
        summary = lines[-2] 
        # Could add a check here: if not command_class in SUPPORTED_COMMAND_CLASSES, it's an issue.
        # But the main function will do that.
        return command_class, summary, None # class, summary, error_message
    elif len(lines) == 1: 
        # If only one line, assume it's the command class, though the prompt asked for two.
        return lines[0], "N/A (LLM provided only one line)", f"Warning: LLM returned only one line for Stage 1. Expected summary and class. Using the line as class."
    else:
        return None, None, "LLM returned too few lines or empty response for Stage 1."
