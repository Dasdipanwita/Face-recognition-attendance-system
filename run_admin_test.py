import traceback

try:
    import app
    import recognizer
    app.app.testing = True
    client = app.app.test_client()
    with client.session_transaction() as sess:
        sess['username'] = 'admin'
        sess['role'] = 'admin'

    resp = client.post('/admin/allowed-users/add', data={'username': 'DebugUserFromTest'}, follow_redirects=True)
    print('STATUS', resp.status_code)
    print(resp.data.decode())
    print('Allowed users now:', recognizer._get_allowed_users())

    # clean up
    recognizer._remove_allowed_user('DebugUserFromTest')
    print('Allowed users after cleanup:', recognizer._get_allowed_users())
except Exception as e:
    print('EXCEPTION')
    traceback.print_exc()
