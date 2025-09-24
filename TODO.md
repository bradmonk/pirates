# LangGraph Tool Calling Fix TODO

## Current Problem
The system is throwing: `Error code: 400 - {'error': {'message': "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.", 'type': 'invalid_request_error', 'param': 'messages.[1].role', 'code': None}}`

## Current Implementation Analysis (ai_agents.py)

### Current Architecture
The current implementation is **NOT using proper LangGraph tool calling patterns**. Instead:

1. **Direct Tool Execution**: Agents directly call `self.game_tools.method()` instead of using LangGraph tool calls
2. **No Tool Message Flow**: No `bind_tools()` or proper tool call → tool result message sequences
3. **Manual State Management**: Agents manually format and store results instead of letting LangGraph handle tool execution
4. **Simple Sequential Flow**: navigator → cannoneer → captain → END with no tool nodes in the flow

### Current Agent Implementations

#### Navigator Agent (Lines 437-565)
```python
def navigator_agent(state: GameAgentState) -> GameAgentState:
    # DIRECT tool execution (not LangGraph tool calling)
    status = self.game_tools.get_game_status()
    scan_result = self.game_tools.navigator.scan_surroundings(radius=5)
    
    # Manual report formatting and storage
    context = f"SCAN RESULTS: {scan_result}..."
    messages = [system_message] + state["messages"] + [HumanMessage(content=context)]
    response = self.llm.invoke(messages)  # No bind_tools()
    
    state["agent_reports"]["navigator"] = response.content
    return state
```

#### Cannoneer Agent (Lines 566-625)  
```python
def cannoneer_agent(state: GameAgentState) -> GameAgentState:
    # DIRECT tool execution
    targets = self.game_tools.cannoneer.get_cannon_targets()
    
    # Manual combat execution and reporting
    if targets:
        combat_result = self.game_tools.cannoneer.fire_cannon(target_position, direction)
    
    # Manual response generation
    response = self.llm.invoke(messages)
    state["agent_reports"]["cannoneer"] = response.content
    return state
```

#### Captain Agent (Lines 626-788)
```python
def captain_agent(state: GameAgentState) -> GameAgentState:
    # DIRECT tool execution
    possible_moves = self.game_tools.captain.get_possible_moves()
    
    # Manual decision making and movement
    decision_match = re.search(r'@(\d+)([NSEW])', response.content)
    if decision_match:
        result = self.game_tools.captain.move_ship(distance, direction)
    
    state["decision"] = response.content
    return state
```

### Current Graph Structure
```python
workflow.add_node("navigator", navigator_agent)
workflow.add_node("cannoneer", cannoneer_agent) 
workflow.add_node("captain", captain_agent)
workflow.add_node("tools", tool_node)  # UNUSED! No edges to it

# Simple sequential flow - tools node is orphaned
workflow.add_edge("navigator", "cannoneer")
workflow.add_edge("cannoneer", "captain") 
workflow.add_edge("captain", END)
```

### Issues with Current Approach
1. **No Tool Call Benefits**: Missing LangGraph's built-in tool calling, validation, error handling
2. **Manual Error Handling**: No automatic retry, validation, or error recovery
3. **No Tool Introspection**: LLM can't "see" available tools or their schemas
4. **Orphaned Tool Node**: `tool_node` is created but never used in the workflow
5. **Complex Manual Parsing**: Manual regex parsing of LLM responses instead of structured tool calls
6. **No Tool Message History**: Tool executions aren't tracked in message history properly

---

## Proposed Solution: Create langgraph_agents.py

### Strategy
Create a completely new implementation using proper LangGraph patterns while keeping the original ai_agents.py as fallback.

## Step-by-Step Implementation Plan

### Phase 1: Core LangGraph Foundation
- [ ] **Step 1.1**: Create `langgraph_agents.py` with proper imports and LangGraph tools
- [ ] **Step 1.2**: Define LangGraph tools using `@tool` decorator for all game functions:
  - `navigate_scan(radius: int = 5) -> str`
  - `fire_cannon(target_position: tuple, direction: str) -> str` 
  - `move_ship(distance: int, direction: str) -> str`
- [ ] **Step 1.3**: Set up proper GameAgentState with message tracking
- [ ] **Step 1.4**: Create LLM instances with proper tool binding

### Phase 2: Individual Agent Implementation
- [ ] **Step 2.1**: **Navigator Agent**
  ```python
  def navigator_agent(state: GameAgentState) -> GameAgentState:
      system_msg = SystemMessage(content="You are the Navigator...")
      human_msg = HumanMessage(content="Scan the area using navigate_scan tool")
      response = llm.bind_tools([navigate_scan]).invoke([system_msg, human_msg])
      state["messages"].append(response)
      return state
  ```

- [ ] **Step 2.2**: **Navigator Result Handler**
  ```python
  def navigator_result_handler(state: GameAgentState) -> GameAgentState:
      # Extract tool results and create readable report
      tool_results = extract_tool_results(state["messages"])
      state["agent_reports"]["navigator"] = format_scan_report(tool_results)
      return state
  ```

- [ ] **Step 2.3**: **Cannoneer Agent**
  ```python
  def cannoneer_agent(state: GameAgentState) -> GameAgentState:
      navigator_report = state["agent_reports"].get("navigator", "No scan data")
      human_msg = HumanMessage(content=f"Based on scan: {navigator_report}, engage targets with fire_cannon")
      response = llm.bind_tools([fire_cannon]).invoke([system_msg, human_msg])
      state["messages"].append(response)
      return state
  ```

- [ ] **Step 2.4**: **Captain Agent & Result Handler**
  Similar pattern for movement decisions

### Phase 3: Proper LangGraph Workflow
- [ ] **Step 3.1**: Create conditional routing functions
  ```python
  def route_after_agent(state: GameAgentState) -> str:
      last_message = state["messages"][-1]
      if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
          return "tools"
      return "next_agent"
  ```

- [ ] **Step 3.2**: Build proper graph with tool integration
  ```python
  workflow.add_conditional_edges(
      "navigator",
      route_after_agent,
      {"tools": "navigator_tools", "next_agent": "cannoneer"}
  )
  workflow.add_edge("navigator_tools", "navigator_result_handler")
  workflow.add_edge("navigator_result_handler", "cannoneer")
  ```

### Phase 4: Tool Result Processing
- [ ] **Step 4.1**: Implement `extract_tool_results(messages)` helper
- [ ] **Step 4.2**: Create report formatting functions for each agent type
- [ ] **Step 4.3**: Ensure proper state management between agent calls

### Phase 5: Integration and Testing  
- [ ] **Step 5.1**: Create `LangGraphPirateGameAgents` class parallel to `PirateGameAgents`
- [ ] **Step 5.2**: Add flag to `pirate_game.py` to choose between implementations
- [ ] **Step 5.3**: Test basic navigator workflow
- [ ] **Step 5.4**: Test full navigator → cannoneer → captain workflow
- [ ] **Step 5.5**: Verify no 400 tool message errors
- [ ] **Step 5.6**: Performance comparison with original implementation

### Phase 6: Migration Path
- [ ] **Step 6.1**: Add configuration option to switch between implementations
- [ ] **Step 6.2**: Comprehensive testing of both versions
- [ ] **Step 6.3**: Documentation and migration guide
- [ ] **Step 6.4**: Deprecate old implementation once stable

## Key LangGraph Patterns to Implement

### IMPORTANT DISCOVERY: Model Requirements
🚨 **Critical Finding**: Proper LangGraph tool calling with `bind_tools()` requires **OpenAI models**. 
- ✅ **OpenAI models (gpt-4o-mini, gpt-4o, etc.)**: Full `bind_tools()` support
- ❌ **Ollama models**: `NotImplementedError` when calling `bind_tools()`
- 📝 **Implication**: For full LangGraph implementation, we need OpenAI API key

**Testing Results**: Navigator Agent successfully implemented and tested with OpenAI gpt-4o-mini:
- ✅ Proper tool calling with `navigate_scan` tool
- ✅ Tool result extraction and report generation  
- ✅ Conditional routing based on tool calls
- ✅ Clean integration with existing game_tools

### Proper Tool Calling Pattern (OpenAI Models)
```python
# 1. Define tools properly
@tool
def navigate_scan(radius: int = 5) -> str:
    """Scan surroundings for treasures and enemies"""
    # Implementation here
    
# 2. Agent calls tool via bind_tools
def navigator_agent(state):
    response = llm.bind_tools([navigate_scan]).invoke(messages)
    state["messages"].append(response)
    return state

# 3. Tool node executes automatically
tool_node = ToolNode([navigate_scan])

# 4. Result handler processes tool outputs  
def result_handler(state):
    tool_results = extract_tool_results(state["messages"])
    state["agent_reports"]["navigator"] = format_results(tool_results)
    return state

# 5. Conditional routing
workflow.add_conditional_edges(
    "navigator",
    lambda state: "tools" if has_tool_calls(state) else "next"
)
```

### Expected Message Flow
```
1. Navigator agent creates tool call message
2. Tool node executes navigate_scan 
3. Tool result message added to state
4. Result handler extracts meaningful report
5. Cannoneer agent receives formatted report
6. Repeat pattern...
```

## Benefits of Proper LangGraph Implementation
✅ **Structured Tool Calls**: No more regex parsing of responses
✅ **Automatic Error Handling**: Built-in tool execution error management  
✅ **Tool Schema Validation**: Automatic parameter validation
✅ **Message History**: Proper tool call/result tracking
✅ **Debugging**: Clear visibility into tool execution
✅ **Extensibility**: Easy to add new tools and agents
✅ **Reliability**: Less prone to parsing errors and malformed responses

## Success Criteria
✅ No 400 tool message errors
✅ Proper tool call → tool result → agent processing flow
✅ Clean separation of concerns (agents make decisions, tools execute actions)
✅ Improved reliability and error handling
✅ Maintainable and extensible codebase
✅ Performance equivalent or better than current implementation

---

## File Structure
```
ai_agents.py          # Original implementation (keep as fallback)
langgraph_agents.py   # New proper LangGraph implementation  
pirate_game.py        # Update to support both implementations
TODO.md              # This file
```