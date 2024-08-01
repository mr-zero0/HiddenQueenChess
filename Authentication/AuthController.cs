using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly AuthService _authService;

    public AuthController(AuthService authService)
    {
        _authService = authService;
    }

    [HttpPost("login")]
    public IActionResult Login([FromBody] LoginRequest request)
    {
        var result = _authService.Login(request.Username, request.Password);
        if (result)
        {
            return Ok(new { success = true });
        }
        else
        {
            return Unauthorized(new { success = false });
        }
    }

    [HttpPost("signup")]
    public IActionResult Signup([FromBody] SignupRequest request)
    {
        var result = _authService.Signup(request.Username, request.Password);
        if (result)
        {
            return Ok(new { success = true });
        }
        else
        {
            return BadRequest(new { success = false });
        }
    }
}
