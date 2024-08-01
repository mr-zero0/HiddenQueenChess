public class AuthService
{
    private readonly Dictionary<string, string> _users = new();

    public bool Login(string username, string password)
    {
        return _users.TryGetValue(username, out var storedPassword) && storedPassword == password;
    }

    public bool Signup(string username, string password)
    {
        if (_users.ContainsKey(username))
        {
            return false;
        }

        _users[username] = password;
        return true;
    }
}
