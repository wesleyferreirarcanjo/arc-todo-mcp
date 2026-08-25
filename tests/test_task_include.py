from app.task_include import project_payload


FAT_TASK = {
    "id": "t1",
    "displayId": "#arc-1",
    "title": "Fix login",
    "description": "alias",
    "businessDescription": "intent",
    "planCodeDescription": "plan",
    "testDescription": "qa essay",
    "status": "todo",
    "isBug": True,
    "bugReason": "stuck",
    "qaChecklistState": {"checkedItemIds": []},
    "assignee": {"id": "u1", "username": "admin"},
    "subtasks": [
        {
            "id": "c1",
            "displayId": "#arc-2",
            "title": "Child",
            "status": "todo",
            "isBug": False,
            "planCodeDescription": "child plan",
            "testDescription": "child qa",
        }
    ],
}


def test_plan_keeps_business_and_plan_drops_qa_and_alias():
    projected = project_payload(FAT_TASK, "plan")
    assert projected["businessDescription"] == "intent"
    assert projected["planCodeDescription"] == "plan"
    assert "testDescription" not in projected
    assert "description" not in projected
    assert "qaChecklistState" not in projected
    assert "assignee" not in projected
    assert projected["subtasks"] == [
        {
            "id": "c1",
            "displayId": "#arc-2",
            "title": "Child",
            "status": "todo",
            "isBug": False,
        }
    ]


def test_summary_drops_all_description_bodies():
    projected = project_payload(FAT_TASK, "summary")
    assert "businessDescription" not in projected
    assert "planCodeDescription" not in projected
    assert projected["title"] == "Fix login"
    assert projected["isBug"] is True


def test_qa_keeps_test_and_bug_fields():
    projected = project_payload(FAT_TASK, "qa")
    assert projected["testDescription"] == "qa essay"
    assert projected["bugReason"] == "stuck"
    assert "planCodeDescription" not in projected


def test_full_drops_description_alias_but_keeps_child_plan():
    projected = project_payload(FAT_TASK, "full")
    assert "description" not in projected
    assert projected["testDescription"] == "qa essay"
    assert projected["subtasks"][0]["planCodeDescription"] == "child plan"
    assert "description" not in projected["subtasks"][0]
