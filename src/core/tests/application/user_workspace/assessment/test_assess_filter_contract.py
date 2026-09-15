def test_assess_story_filters_reject_invalid_canonical_value(client, auth_header):
    response = client.get("/api/assess/stories?sort=invalid", headers=auth_header)

    assert response.status_code == 400
