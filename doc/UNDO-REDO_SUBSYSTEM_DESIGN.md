# Undo/Redo System Design Document

## 1. Overview

This document outlines the architecture and principles of the undo/redo subsystem for the MSX Tile Forge application. The system's design goals are robustness, maintainability, and flexibility, allowing for user actions to be reversible.

The architecture is based on the **Command Design Pattern**. Each undoable action is encapsulated into a self-contained "command" object. These objects are managed by a central `UndoManager` which maintains the history of actions.

This implementation uses a **hybrid approach**, leveraging two types of command patterns to balance correctness, performance, and memory usage:
1.  **State-Based (Memento) Pattern:** For large, infrequent, or structurally complex operations.
2.  **Procedural Pattern:** For small, frequent, and easily reversible operations.

## 2. Core Principles

To maintain data integrity and prevent state corruption, all command implementations adhere to the following principles of **State Isolation**:

1.  **Immutable Command State:** A command must immutably capture all information necessary to perform and reverse its operation at the moment of its creation. For state-based commands, this is achieved by storing a `deepcopy` of the relevant "before" (and sometimes "after") state. For procedural commands, this means storing the primitive values of the change.

2.  **Operate on Live Data:** A command's `execute()` and `undo()` methods must only modify the application's "live" global data structures. They must not create links or references from the live data back to the command's internal state.

3.  **Isolate on Restoration:** When restoring a state (typically in an `undo()` method), the command must apply a `deepcopy` of its stored state back to the live data. This prevents future user actions from modifying the command's internal history.

## 3. Architecture

The subsystem consists of three main components: the Command Interface, the Undo Manager, and the concrete Command Implementations.

### 3.1. The Command Interface (`ICommand`)

`ICommand` is an abstract base class that defines the contract for all undoable actions.

-   **Purpose:** To ensure that any command can be treated polymorphically by the `UndoManager`.
-   **Structure:**
    -   `__init__(self, description)`: The constructor stores a user-friendly string describing the action (e.g., "Paint Pixel," "Clear Map").
    -   `execute(self)`: Applies the command's action to the live application data.
    -   `undo(self)`: Reverts the command's action, restoring the application data to its previous state.

### 3.2. The Command Engine (`UndoManager`)

`UndoManager` is the central controller for the entire subsystem. It is responsible for executing commands and managing the history stacks.

-   **State:**
    -   `undo_stack`: A list of `ICommand` objects that have been executed and can be undone.
    -   `redo_stack`: A list of `ICommand` objects that have been undone and can be redone.

-   **Core Methods:**
    -   `execute(command)`: The primary entry point for a new user action. It calls the command's `execute()` method, then pushes the command onto the `undo_stack` and clears the `redo_stack`.
    -   `register(command)`: Pushes a command that has *already been executed* onto the undo stack. This is used for actions that require live feedback, such as a paint stroke.
    -   `undo()`: Pops the last command from the `undo_stack`, calls its `undo()` method, and pushes it onto the `redo_stack`.
    -   `redo()`: Pops the last command from the `redo_stack`, calls its `execute()` method, and pushes it back onto the `undo_stack`.

### 3.3. Command Implementations

Concrete command classes implement the `ICommand` interface. They contain the actual logic for an action and its reversal. The choice of implementation pattern is critical.

## 4. Command Patterns in Use

The system utilizes two patterns based on the nature of the operation.

### 4.1. State-Based (Memento) Pattern

This pattern is used for large-scale or structurally complex data changes.

-   **How it Works:** The command object stores a full `deepcopy` of the relevant portion of the application's state *before* the modification. The `undo` method restores this saved state.
-   **When to Use:**
    -   Large, structural changes (resizing, clearing).
    -   Operations where the inverse is difficult to calculate.
    -   Infrequent actions where the performance cost of `deepcopy` is acceptable.
-   **Key Examples in Code:**
    -   `ClearMapCommand`: Stores a `deepcopy` of the entire `map_data`.
    -   `SetTilesetLimitCommand`: This command captures deep copies of the `tileset_patterns`, `tileset_colors`, `supertiles_data`, and selection indices for both its "before" and "after" states.

### 4.2. Procedural Pattern

This pattern is used for performance-sensitive, frequent, and simple operations.

-   **How it Works:** The command object stores the *parameters* of the change, including the "before" and "after" values of the specific data that was modified. It does **not** store a snapshot of the entire data structure.
-   **When to Use:**
    -   High-frequency actions (e.g., painting during a mouse drag).
    -   Simple, easily reversible value changes.
    -   Modifying a small part of a very large data structure.
-   **Key Examples in Code:**
    -   `PaintPixelCommand`: Stores only the tile index, coordinates, old value, and new value. This approach is lightweight in terms of memory.
    -   `UpdateSupertileRefsFor...` commands: These are procedural commands that perform complex reference updates algorithmically, avoiding the need to store any large state copies.

## 5. Significant Command Particularities

-   **`CompositeCommand`:** This is a structural command that groups a list of other commands into a single, atomic undo/redo step. It is used for features like "Paint Stroke," where a single user gesture generates multiple individual commands.
-   **`ModifyListCommand`:** A state-based command for handling `list.insert()` and `list.pop()`. It performs a `deepcopy` on the *value* being inserted or removed, ensuring the integrity of the command's internal state.
-   **`SetDataCommand`:** A generic state-based command that can replace any data structure. It serves as a clean abstraction for many state-change operations.

## 6. Opportunities for Enhancement

The following enhancements could improve maintainability, performance, and user experience.

1.  **Centralize Side-Effect Handling:**
    *   **Problem:** Side-effect logic (marking the project modified, invalidating caches, refreshing the UI) is duplicated across many command classes.
    *   **Solution:** Move this logic into the `UndoManager`. After a command's `execute()` or `undo()` is called, the `UndoManager` would be responsible for triggering the necessary application-wide updates. This would simplify command classes and enforce consistency.

2.  **Implement Command Coalescing:**
    *   **Problem:** Repeatedly performing the same action (e.g., shifting a tile five times) creates five separate undo steps.
    *   **Solution:** Enhance the `UndoManager` to merge consecutive, compatible commands into a single command on the undo stack. For example, merging five "Shift Up" commands into one "Shift Up (x5)" command.

3.  **Memory Optimization with the "Diff" Pattern:**
    *   **Problem:** State-based commands for very large data structures (like the map) can consume significant memory.
    *   **Solution:** For these commands, instead of storing a full `deepcopy`, store only the "diff"—a list of the specific changes made. The `undo` method would then apply the inverse of this diff. This trades implementation complexity for a reduction in memory usage.

4.  **Create a User-Facing Undo History Viewer:**
    *   **Problem:** The user can only undo one step at a time and has no visual representation of their action history.
    *   **Solution:** Create a "History" panel (similar to those in graphics editors) that displays the `description` of each command in the undo stack. This would allow the user to see their recent actions and jump back multiple steps at once.

## 7. Maintenance Guide for New Commands

When adding a new undoable action, follow these steps:

1.  **Create a New Class:** Inherit from `ICommand`.
2.  **Choose a Pattern:**
    *   Is the action frequent, simple, and performance-critical (like painting a single pixel)? Use the **Procedural Pattern**.
    *   Is the action complex, structural, or infrequent (like resizing the map)? Use the **State-Based Pattern** with `copy.deepcopy()`.
3.  **Implement `__init__`:** Capture all necessary data for both `execute` and `undo`, adhering to the **Immutable Command State** principle.
4.  **Implement `execute()` and `undo()`:** Write the logic to modify the live application data, adhering to the **State Isolation** principles.
5.  **Integrate into the UI:** In the relevant UI event handler, instead of modifying the live data directly, instantiate your new command object and pass it to `undo_manager.execute()`.