from dwg.labels import lenient_correct


def test_lenient_accepts_a_lookup_before_a_write_but_not_a_different_write():
    # mock: gold actions list only create_task; get_users is ToolType.READ
    assert lenient_correct("create_task", "create_task", "mock", "create_task_1")
    assert lenient_correct("get_users", "create_task", "mock", "create_task_1")
    assert not lenient_correct("update_task_status", "create_task", "mock", "create_task_1")


def test_lenient_lookup_instead_of_replying_needs_the_lookup_in_gold_actions():
    # airline task 0's gold actions are empty; replying was the reference
    assert not lenient_correct("get_user_details", "respond_to_user", "airline", "0")
