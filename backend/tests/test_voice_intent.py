"""Tests for voice intent classification."""

from clarity_backend.voice.intent import (
    CHECK_STATUS,
    CREATE_ISSUE,
    DISMISS_ITEM,
    FIX_ITEM,
    MORNING_BRIEF,
    PLANE_COMPLETE_TASK,
    PLANE_CREATE_TASK,
    PLANE_LIST_TASKS,
    QUERY_ERRORS,
    QUERY_VULNS,
    SNOOZE_ITEM,
    UNKNOWN,
    classify,
)


class TestClassifyErrors:
    def test_what_errors_today(self):
        intent = classify("What errors came in today?")
        assert intent.type == QUERY_ERRORS
        assert intent.params.get("timeframe") == "24h"

    def test_any_bugs(self):
        intent = classify("Are there any bugs?")
        assert intent.type == QUERY_ERRORS

    def test_critical_errors(self):
        intent = classify("Show me critical errors")
        assert intent.type == QUERY_ERRORS
        assert intent.params.get("severity") == "critical"

    def test_failing_this_week(self):
        intent = classify("What's been failing this week?")
        assert intent.type == QUERY_ERRORS
        assert intent.params.get("timeframe") == "7d"


class TestClassifyVulns:
    def test_vulnerabilities(self):
        intent = classify("Any new vulnerabilities?")
        assert intent.type == QUERY_VULNS

    def test_security_issues(self):
        intent = classify("Are there security issues?")
        assert intent.type == QUERY_VULNS

    def test_cve(self):
        intent = classify("Any CVE reports?")
        assert intent.type == QUERY_VULNS


class TestClassifyStatus:
    def test_status(self):
        intent = classify("What's my status?")
        assert intent.type == CHECK_STATUS

    def test_overview(self):
        intent = classify("Give me an overview")
        assert intent.type == CHECK_STATUS

    def test_how_are_things(self):
        intent = classify("How are things going?")
        assert intent.type == CHECK_STATUS


class TestClassifyActions:
    def test_create_issue(self):
        intent = classify("Create an issue for item #42")
        assert intent.type == CREATE_ISSUE
        assert intent.params.get("item_id") == 42

    def test_snooze(self):
        intent = classify("Snooze item 5")
        assert intent.type == SNOOZE_ITEM
        assert intent.params.get("item_id") == 5

    def test_dismiss(self):
        intent = classify("Dismiss this one")
        assert intent.type == DISMISS_ITEM

    def test_morning_brief(self):
        intent = classify("Give me the morning brief")
        assert intent.type == MORNING_BRIEF


class TestClassifyFixItem:
    def test_fix_item_3(self):
        intent = classify("fix item 3")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 3

    def test_auto_fix_error_5(self):
        intent = classify("auto-fix error 5")
        assert intent.type == FIX_ITEM

    def test_patch_vulnerability(self):
        intent = classify("patch vulnerability #7")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 7

    def test_repair_issue(self):
        intent = classify("repair issue 12")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 12

    def test_resolve_item(self):
        intent = classify("resolve item 1")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 1


class TestClassifyEdgeCases:
    def test_empty_string(self):
        intent = classify("")
        assert intent.type == UNKNOWN
        assert intent.confidence == 0.0

    def test_unrecognized(self):
        intent = classify("Tell me a joke about cats")
        assert intent.type == UNKNOWN

    def test_confidence_for_match(self):
        intent = classify("Show errors")
        assert intent.confidence > 0.5

    def test_case_insensitive(self):
        intent = classify("SHOW ME ALL ERRORS")
        assert intent.type == QUERY_ERRORS


class TestClassifyPlaneCreateTask:
    def test_create_task_with_colon(self):
        intent = classify("create task in acme: fix the login bug")
        assert intent.type == PLANE_CREATE_TASK
        assert intent.params["project_name"] == "acme"
        assert intent.params["task_title"] == "fix the login bug"

    def test_create_task_without_colon(self):
        intent = classify("create task in acme fix the login bug")
        assert intent.type == PLANE_CREATE_TASK
        assert intent.params["project_name"] == "acme"
        assert "fix" in intent.params.get("task_title", "")

    def test_create_urgent_task(self):
        intent = classify("create urgent task in clarity: update docs")
        assert intent.type == PLANE_CREATE_TASK
        assert intent.params["priority"] == "urgent"
        assert intent.params["project_name"] == "clarity"

    def test_add_ticket_for_project(self):
        intent = classify("add ticket for widgets: new feature")
        assert intent.type == PLANE_CREATE_TASK
        assert intent.params["project_name"] == "widgets"

    def test_new_work_item(self):
        intent = classify("new work item in internal: refactor API")
        assert intent.type == PLANE_CREATE_TASK

    def test_does_not_clash_with_create_issue(self):
        """'create task in X' should be PLANE_CREATE_TASK, not CREATE_ISSUE."""
        intent = classify("create task in acme: do something")
        assert intent.type == PLANE_CREATE_TASK


class TestClassifyPlaneCompleteTask:
    def test_complete_task_with_ref(self):
        intent = classify("complete task ACME-42")
        assert intent.type == PLANE_COMPLETE_TASK
        assert intent.params["task_ref"] == "acme-42"

    def test_done_with_task(self):
        intent = classify("done with task widgets-5")
        assert intent.type == PLANE_COMPLETE_TASK
        assert "widgets-5" in intent.params["task_ref"]

    def test_finish_ticket(self):
        intent = classify("finish ticket int-12")
        assert intent.type == PLANE_COMPLETE_TASK

    def test_close_item(self):
        intent = classify("close item CLR-99")
        assert intent.type == PLANE_COMPLETE_TASK


class TestClassifyPlaneListTasks:
    def test_show_my_tasks(self):
        intent = classify("show my tasks")
        assert intent.type == PLANE_LIST_TASKS

    def test_list_tasks_in_project(self):
        intent = classify("list tasks in acme")
        assert intent.type == PLANE_LIST_TASKS
        assert intent.params["project_name"] == "acme"

    def test_what_are_my_tickets(self):
        intent = classify("what are my tickets")
        assert intent.type == PLANE_LIST_TASKS

    def test_check_work_items(self):
        intent = classify("check my work items")
        assert intent.type == PLANE_LIST_TASKS
