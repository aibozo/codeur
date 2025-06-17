# Git Workflow Integration Guide

## Overview

This guide explains how to integrate the new Git workflow system with the existing multi-agent architecture. The workflow provides atomic commits, safe branching, checkpoints, and easy reversion capabilities.

## Integration Points

### 1. Update GitOperations in Coding Agent

The existing `GitOperations` class should be extended to use the new `GitWorkflow`:

```python
# In src/coding_agent/integrated_coding_agent.py

async def _create_task_branch(self, task: CodingTask):
    """Create a branch for the task using new workflow."""
    self.git_workflow = GitWorkflow(
        self.project_path,
        event_bridge=self.event_bridge
    )
    
    branch_name = await self.git_workflow.create_task_branch(
        task_id=task.id,
        description=task.title,
        agent_id=self.agent_id
    )
    
    return branch_name

async def _commit_changes(self, task: CodingTask, message: str):
    """Create atomic commit for task."""
    commit_sha = await self.git_workflow.commit_atomic(
        task_id=task.id,
        agent_id=self.agent_id,
        message=message,
        commit_type=CommitType.FEATURE,
        metadata={
            'files_modified': task.files_to_modify,
            'tests_passed': True,
            'parent_plan': task.metadata.get('plan_id')
        }
    )
    
    return commit_sha
```

### 2. Update Branch Manager

Replace the existing `BranchManager` logic with the new workflow:

```python
# In src/core/branch_manager.py

class BranchManager:
    def __init__(self, project_path: Path, event_bridge: EventBridge):
        self.git_workflow = GitWorkflow(
            str(project_path),
            event_bridge=event_bridge
        )
        self.safety_guard = GitSafetyGuard(str(project_path))
    
    async def merge_task_branches(self, task_ids: List[str]):
        """Merge completed task branches to working branch."""
        for task_id in task_ids:
            # Run pre-merge checks
            validation = await self.safety_guard.run_pre_merge_checks(
                source_branch=f"task/{task_id}",
                target_branch=self.git_workflow._find_working_branch()
            )
            
            if validation.can_proceed:
                success, message = await self.git_workflow.merge_task_to_working(
                    task_id=task_id,
                    agent_id="branch_manager",
                    strategy=MergeStrategy.SQUASH
                )
```

### 3. Add Safety Checks to Agent Base

Integrate safety checks into the base agent class:

```python
# In src/core/integrated_agent_base.py

async def pre_commit_validation(self) -> bool:
    """Run safety checks before committing."""
    if not hasattr(self, 'safety_guard'):
        self.safety_guard = GitSafetyGuard(self.project_path)
    
    validation = await self.safety_guard.run_pre_commit_checks(self.agent_id)
    
    if not validation.can_proceed:
        # Log failures
        for result in validation.results:
            if result.status == CheckStatus.FAILED:
                self.logger.error(f"Safety check failed: {result.message}")
        
        # Attempt auto-fixes if available
        for result in validation.results:
            if result.auto_fixable and result.fix_command:
                self.logger.info(f"Attempting auto-fix: {result.fix_command}")
                # Run fix command
    
    return validation.can_proceed
```

### 4. Add Checkpoint Creation to Architect

The Architect should create checkpoints at key milestones:

```python
# In src/architect/architect.py

async def create_milestone_checkpoint(self, description: str):
    """Create a checkpoint when reaching a milestone."""
    if hasattr(self, 'git_workflow'):
        checkpoint = await self.git_workflow.create_checkpoint(
            description=description,
            auto=False
        )
        
        # Store checkpoint reference in task graph
        self.task_graph.add_checkpoint(checkpoint.id)
```

### 5. Update UI Components

Add git visualization to the terminal UI:

```python
# In src/ui/terminal/components.py

class GitHistoryPanel(Panel):
    """Panel showing git history visualization."""
    
    def __init__(self, git_visualizer: GitVisualizer):
        super().__init__("Git History")
        self.git_visualizer = git_visualizer
    
    def render(self) -> str:
        graph = self.git_visualizer.generate_graph(max_commits=20)
        return self.git_visualizer.render_terminal(graph, width=self.width)
```

### 6. Add Reversion Commands

Add commands for reverting tasks:

```python
# In src/cli/commands/revert.py

@click.command()
@click.argument('task_id')
@click.option('--cascade', is_flag=True, help='Revert dependent tasks')
async def revert_task(task_id: str, cascade: bool):
    """Revert changes made by a specific task."""
    workflow = GitWorkflow(os.getcwd())
    
    result = await workflow.revert_task(task_id, cascade=cascade)
    
    if result.success:
        click.echo(f"✅ Successfully reverted task {task_id}")
        click.echo(f"   Affected files: {', '.join(result.affected_files)}")
        if result.cascade_reverts:
            click.echo(f"   Cascade reverted: {', '.join(result.cascade_reverts)}")
    else:
        click.echo(f"❌ Failed to revert: {result.message}")
```

## Configuration

### 1. Update Agent Configuration

Add git workflow settings to agent configs:

```yaml
# In config/agents.yaml

coding_agent:
  git_workflow:
    enable_atomic_commits: true
    auto_merge_to_working: true
    merge_strategy: squash
    
architect:
  git_workflow:
    create_checkpoints: true
    checkpoint_triggers:
      - milestone_complete
      - before_major_refactor
      - after_test_suite_pass
    
safety_guard:
  max_file_size: 10485760  # 10MB
  secret_patterns:
    - 'custom_api_key_pattern'
  protected_files:
    - '.env'
    - 'secrets.yaml'
```

### 2. Environment Variables

```bash
# Git workflow configuration
export GIT_WORKFLOW_ENABLED=true
export GIT_SAFETY_CHECKS=true
export GIT_AUTO_CHECKPOINT=true
export GIT_VISUALIZER_ENABLED=true
```

## Migration Steps

### Step 1: Update Dependencies

```bash
pip install gitpython  # For advanced git operations
pip install pygit2    # Optional: for performance
```

### Step 2: Update Existing Code

1. Replace direct git operations with `GitWorkflow` methods
2. Add safety checks before commits
3. Update branch creation to use naming conventions
4. Add checkpoint creation at key points

### Step 3: Database Schema Updates

If using a database to track git operations:

```sql
-- Add tables for tracking git workflow
CREATE TABLE git_checkpoints (
    id VARCHAR(12) PRIMARY KEY,
    branch_name VARCHAR(255),
    commit_sha VARCHAR(40),
    description TEXT,
    created_at TIMESTAMP,
    created_by VARCHAR(50),
    metadata JSONB
);

CREATE TABLE git_task_commits (
    task_id VARCHAR(50),
    commit_sha VARCHAR(40),
    agent_id VARCHAR(50),
    created_at TIMESTAMP,
    reversible BOOLEAN DEFAULT true,
    PRIMARY KEY (task_id, commit_sha)
);
```

### Step 4: Update Event Handlers

Add handlers for new git events:

```python
# In event handlers

@event_handler("git.task.completed")
async def on_task_completed(event: Dict[str, Any]):
    task_id = event['task_id']
    # Update task status in UI
    # Trigger next task if dependencies met
    
@event_handler("git.checkpoint.created")
async def on_checkpoint_created(event: Dict[str, Any]):
    checkpoint_id = event['checkpoint_id']
    # Update UI with checkpoint indicator
    # Log checkpoint for audit trail
```

## Testing

### 1. Unit Tests

```python
# tests/test_git_workflow.py

async def test_atomic_commit():
    """Test atomic commit functionality."""
    workflow = GitWorkflow(test_repo_path)
    
    # Create task branch
    branch = await workflow.create_task_branch("TEST-001", "test task", "test-agent")
    
    # Make changes and commit
    commit_sha = await workflow.commit_atomic(
        "TEST-001", "test-agent", "Test commit"
    )
    
    assert commit_sha is not None
    assert "TEST-001" in workflow.task_commits
```

### 2. Integration Tests

```python
# tests/test_git_integration.py

async def test_full_workflow():
    """Test complete git workflow integration."""
    # Start session
    # Create multiple tasks
    # Run safety checks
    # Merge to working
    # Create checkpoint
    # Revert a task
    # Restore from checkpoint
```

## Monitoring

### 1. Metrics to Track

- Commits per task
- Average time between checkpoints
- Reversion frequency
- Safety check failures
- Merge conflicts

### 2. Logging

```python
# Enhanced logging for git operations
logger.info("Git operation", extra={
    'operation': 'commit',
    'task_id': task_id,
    'agent_id': agent_id,
    'branch': current_branch,
    'files_changed': len(files),
    'safety_checks_passed': validation.can_proceed
})
```

## Best Practices

1. **Always use atomic commits** - One task = one commit
2. **Run safety checks** - Never skip pre-commit validation
3. **Create regular checkpoints** - At least every 4 hours or major milestone
4. **Use descriptive branch names** - Follow the naming conventions
5. **Document reversion reasons** - When reverting, always provide context
6. **Test merge conflicts locally** - Before attempting automated merges
7. **Monitor git history** - Use visualizer to track progress

## Troubleshooting

### Common Issues

1. **Merge Conflicts**
   - Use the conflict resolution protocol
   - Escalate to architect if needed

2. **Failed Safety Checks**
   - Review the validation report
   - Fix issues or request override

3. **Checkpoint Restoration**
   - Verify checkpoint exists
   - Choose appropriate restore strategy

4. **Performance Issues**
   - Enable git garbage collection
   - Limit visualization to recent commits

## Future Enhancements

1. **Advanced Conflict Resolution**
   - ML-based conflict resolution
   - Semantic merge strategies

2. **Distributed Git Support**
   - Multi-repository workflows
   - Cross-team collaboration

3. **Enhanced Visualization**
   - 3D git history
   - Real-time collaboration view

4. **Audit Trail**
   - Blockchain-backed commit history
   - Compliance reporting