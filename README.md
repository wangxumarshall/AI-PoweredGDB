# AI-PoweredGDB
Harness the power of ChatGPT inside the GDB/LLDB debugger!


AI-PoweredGDB is a tool designed to superpower your debugging experience with GDB or LLDB, debuggers for compiled languages. Use it to accelerate your debugging workflow by leveraging the power of ChatGPT to assist you while using GDB/LLDB! 

It allows you to explain in natural language what you want to do, and then automatically execute the relevant command. Optionally, you can ask ChatGPT to explain the command it just ran or even pass in any question for it to answer. AI-PoweredGDB now also offers more advanced AI-powered features like automated program state exploration and contextual assistance when your program stops. Focus on what's important - figuring out that nasty bug instead of chasing down GDB/LLDB commands at the tip of your tongue.

![Image](https://lh5.googleusercontent.com/xZMLwWWxavqYjC3fyCIZJ0m-s-f-XEoiOeWGbxRrw3dWoukUoWzJJ4iiBkVO2Vtiyr4K6o0WkTs7B40TapeBPIYwgVRVhDXGVjB4tFYoKH3_nK847nYXl3pISB6dEP6Wp_o0uPlfJOjCrLspm0_VNw)

## Contents

1. [Installation](#installation-intructions)
2. [Updating](#updating)
3. [Usage](#usage)
    * [Key Features](#key-features)
    * [GDB-Specific `chat` Command Enhancements](#gdb-specific-chat-command-enhancements)
    * [Advanced GDB Features](#advanced-gdb-features)
        * [Setting Interaction Mode: `chat-set-mode`](#setting-interaction-mode-chat-set-mode)
        * [Automated Program State Exploration: `chat-explore` (GDB)](#automated-program-state-exploration-chat-explore-gdb)
        * [Contextual Assistance on Stop (GDB)](#contextual-assistance-on-stop-gdb)
4. [Contributing](#contributing)
5. [Getting Updates](#getting-updates)

### Installation instructions
First, make sure you install [pip](https://pip.pypa.io/en/stable/installation/). AI-PoweredGDB also
requires a python version of 3.3 or above.

To install, run the command 

```pip3 install AI-PoweredGDB```. 

It will create an executable called ```AI-PoweredGDB``` that you will have to use to set your api key. 
To do that, run the command

```AI-PoweredGDB -k <API KEY> ```

You can set the model to use. There are two possible options, ```gpt-3.5-turbo``` and ```gpt-4```(defaulting to the former):

```AI-PoweredGDB -m <MODEL>```

You can also use a custom model name if you have a specialized fine-tuned model (e.g., `custom_gdb_model`):
```AI-PoweredGDB -m custom_gdb_model```
Ensure your API endpoint (set via `AI-PoweredGDB -u <api-url>`) is configured to serve this model.

If you are using a non-official api provider, you can also set the api url:

```AI-PoweredGDB -u <api-url>```

This information is stored in text in the same directory as the installed script, which is currently in your python site packages
folder along with the main script. You can easily find this location by running the following in your terminal:

``` python -m site --user-site```

Optionally, you can also download the compressed files in the releases page to get the scripts directly.
If you do this, navigate to the ```AI-PoweredGDB``` folder, and you can install with

```pip3 install .```.

### Updating

To update AI-PoweredGDB, run the following

```pip3 install AI-PoweredGDB --upgrade```


### Usage
For GDB usage, I first recommend editing your ```$HOME/.gdbinit``` to source the main script automatically on startup. Run the following command:

```echo "source $(python -m site --user-site)/AI-PoweredGDB/gdb.py" > $HOME/.gdbinit```

The same applies for LLDB. Edit your ```$HOME/.lldbinit``` and run the following command:

```echo "command script import $(python -m site --user-site)/AI-PoweredGDB/lldb.py" > $HOME/.lldbinit```

#### Key Features
- **Natural Language to Debugger Commands:** Translate your plain English debugging queries into the correct GDB or LLDB commands.
- **Command Explanations:** Ask AI-PoweredGDB to explain the command it just executed or any other debugging concept.
- **Real-time AI Interaction:** All responses from the AI (generated commands, explanations, suggestions) are now streamed token-by-token, providing a more interactive and real-time experience.

While inside your debugger, you can run the command `chat` appended by your query. For example, `chat list all breakpoints that I created`. 
There is also a command called `explain` that you can use with no arguments to explain the previously run command, 
and optionally, with a query to just ask GPT a question. For example, running `explain` directly after running 
`break 7` would prompt the tool to explain how breakpoints work. Running `explain how input formatting works in gdb` 
would prompt it to explain input formatting (see the image at the top).

Run `chat help` to print out a short tutorial on how to use the tool.

#### GDB-Specific `chat` Command Enhancements
The `chat` command in GDB now uses an advanced multi-stage reasoning process. It intelligently classifies your query, consults GDB's help documentation, and refines its understanding through several AI-powered steps to generate the most accurate GDB command. You may see diagnostic messages in the GDB console indicating these internal stages (e.g., "Stage 1: Classifying...", "Stage 2: Getting help..."). This makes the command generation more robust, especially for complex or nuanced queries.

### Advanced GDB Features

#### Setting Interaction Mode: `chat-set-mode`
You can control how `chat` executes commands using `chat-set-mode`:
*   `chat-set-mode agent`: (Default) AI-PoweredGDB executes the AI-generated command immediately.
*   `chat-set-mode ask`: AI-PoweredGDB will show you the AI-generated command and ask for your confirmation (y/n) before executing it.

Example in GDB:
```gdb
(gdb) chat-set-mode ask
AI-PoweredGDB mode set to: Ask
(gdb) chat print myVariable
Suggested command: print myVariable
Execute? (y/n): y
$1 = 10 
(gdb) chat-set-mode agent
AI-PoweredGDB mode set to: Agent
```
*(Note: The `chat-set-mode` command is also available in LLDB with the same functionality.)*

#### Automated Program State Exploration: `chat-explore` (GDB)
For more complex debugging scenarios, use the `chat-explore` command. Provide an initial query, and AI-PoweredGDB will use the AI to suggest and execute a series of GDB commands to help you investigate.

How it works:
1. You provide a query (e.g., "why is my_pointer null?").
2. AI-PoweredGDB and the AI determine an initial GDB command.
3. The command is executed, and its output is shown.
4. The AI then suggests the next command based on the history, or provides a hypothesis or conclusion.
5. This process repeats for a few steps or until a conclusion is reached.

Example in GDB:
```gdb
(gdb) chat-explore why ptr is 0x0
Starting exploration for: why ptr is 0x0
--- Exploration Step 1/3 ---
Initial command: print ptr
Executing: print ptr
Output:
$1 = (void *) 0x0
LLM Suggestion (raw):
info var ptr
--- Exploration Step 2/3 ---
Executing: info var ptr
Output:
ptr = (void *) 0x0
LLM Suggestion (raw):
HYPOTHESIS: The variable 'ptr' was either not initialized or was explicitly set to NULL. Check where 'ptr' is assigned a value.
LLM Hypothesis: The variable 'ptr' was either not initialized or was explicitly set to NULL. Check where 'ptr' is assigned a value.
--- Exploration Finished ---
```

#### Contextual Assistance on Stop (GDB)
When GDB stops (e.g., at a breakpoint or after a step command), AI-PoweredGDB automatically provides contextual assistance:
1.  **Current Debugging Context:** Displays information about the current frame, including function name, file, line number, arguments, and local variables.
2.  **AI-Powered Suggestions:** Offers brief suggestions or common next debugging steps based on the current context.

This feature requires no special commands and triggers automatically. Example output on stop:
```gdb
Breakpoint 1, main () at test.c:5
5	    int x = 10;

--- AI-PoweredGDB Contextual Assistance ---
Stopped at: Function: main, PC: 0x5555555552dc, File: test.c, Line: 5
Arguments: No arguments found or info args failed.
Locals:
No locals found or info locals failed.
AI-PoweredGDB Suggestion: Consider using 'next' to step over the current line or 'print x' after this line to check its value.
--- End Contextual Assistance ---
```

### Contributing
Thanks for your interest in contributing to AI-PoweredGDB! See [CONTRIBUTING.md](CONTRIBUTING.md) on ways to
help the development effort. 

### Staying Updated

If you'd like to stay up-to-date on new features/fixes, follow my [twitter](https://twitter.com/pranay__gosar). There's plenty
of exciting features on the horizon such as complete context-awareness that will make it possible
for AI-PoweredGDB to not only help you use GDB, but to help you fix the code itself.
