using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;

[Route("api/[controller]")]
[ApiController]
public class AuthController : ControllerBase
{
    private readonly AuthService _authService;

    public AuthController(AuthService authService)
    {
        _authService = authService;
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        var result = await _authService.ValidateUserAsync(request.Username, request.Password);
        if (result)
        {
            return Ok(new { success = true });
        }
        return Unauthorized(new { success = false, message = "Invalid credentials" });
    }

    [HttpPost("signup")]
    public async Task<IActionResult> Signup([FromBody] SignupRequest request)
    {
        var result = await _authService.RegisterUserAsync(request.Username, request.Password);
        if (result)
        {
            return Ok(new { success = true });
        }
        return BadRequest(new { success = false, message = "User registration failed" });
    }
}
