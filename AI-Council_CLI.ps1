[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Prompt,

    [string]$GptModel = '',

    [string]$ClaudeModel = '',

    [ValidateRange(1, 3600)]
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$interactiveMode = [string]::IsNullOrWhiteSpace($Prompt)

function Invoke-Cli {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$InputText,

        [Parameter(Mandatory)]
        [int]$Timeout
    )

    $commands = @(Get-Command $Name -CommandType Application -All -ErrorAction SilentlyContinue)
    $command = $commands |
        Where-Object { $_.Path -like '*.exe' } |
        Select-Object -First 1

    if (-not $command) {
        $command = $commands |
            Where-Object { $_.Path -like '*.cmd' } |
            Select-Object -First 1
    }

    if (-not $command) {
        return [pscustomobject]@{
            Name = $Name
            ExitCode = $null
            TimedOut = $false
            StdOut = ''
            StdErr = "Command not found: $Name"
        }
    }

    function ConvertTo-NativeArgument {
        param([AllowEmptyString()][string]$Value)

        if ($Value -notmatch '[\s"]') {
            return $Value
        }

        $builder = New-Object System.Text.StringBuilder
        [void]$builder.Append('"')
        $backslashes = 0

        foreach ($character in $Value.ToCharArray()) {
            if ($character -eq '\') {
                $backslashes++
                continue
            }

            if ($character -eq '"') {
                [void]$builder.Append((('\' * (($backslashes * 2) + 1)) -join ''))
                [void]$builder.Append('"')
            }
            else {
                [void]$builder.Append((('\' * $backslashes) -join ''))
                [void]$builder.Append($character)
            }
            $backslashes = 0
        }

        [void]$builder.Append((('\' * ($backslashes * 2)) -join ''))
        [void]$builder.Append('"')
        return $builder.ToString()
    }

    $nativeArguments = @($Arguments)
    $commandPath = $command.Source

    if ($command.Path -like '*.cmd') {
        $commandPath = $env:ComSpec
        $nativeArguments = @('/d', '/s', '/c', $command.Source) + $nativeArguments
    }

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $commandPath
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.CreateNoWindow = $true

    if ($startInfo.PSObject.Properties.Name -contains 'StandardOutputEncoding') {
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        $startInfo.StandardOutputEncoding = $utf8
        $startInfo.StandardErrorEncoding = $utf8
    }

    $startInfo.Arguments = (($nativeArguments | ForEach-Object {
        ConvertTo-NativeArgument -Value ([string]$_)
    }) -join ' ')

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo

    try {
        [void]$process.Start()
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $inputBytes = [System.Text.Encoding]::UTF8.GetBytes($InputText)
        $process.StandardInput.BaseStream.Write($inputBytes, 0, $inputBytes.Length)
        $process.StandardInput.BaseStream.Flush()
        $process.StandardInput.Close()

        $finished = $process.WaitForExit($Timeout * 1000)
        if (-not $finished) {
            try { $process.Kill($true) } catch { $process.Kill() }
            $process.WaitForExit()
        }

        [pscustomobject]@{
            Name = $Name
            ExitCode = if ($finished) { $process.ExitCode } else { $null }
            TimedOut = -not $finished
            StdOut = $stdoutTask.GetAwaiter().GetResult().Trim()
            StdErr = $stderrTask.GetAwaiter().GetResult().Trim()
        }
    }
    catch {
        [pscustomobject]@{
            Name = $Name
            ExitCode = $null
            TimedOut = $false
            StdOut = ''
            StdErr = $_.Exception.Message
        }
    }
    finally {
        $process.Dispose()
    }
}

function Write-Result {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [pscustomobject]$Result
    )

    Write-Host "`n[$Label]"

    if ($Result.TimedOut) {
        Write-Host "ERROR: Timed out after $TimeoutSeconds seconds." -ForegroundColor Red
    }
    elseif ($null -eq $Result.ExitCode) {
        Write-Host "ERROR: $($Result.StdErr)" -ForegroundColor Red
    }
    elseif ($Result.ExitCode -ne 0) {
        Write-Host "ERROR: Process exited with code $($Result.ExitCode)." -ForegroundColor Red
    }

    if ($Result.StdOut) {
        Write-Output $Result.StdOut
    }

    if (($Result.TimedOut -or $null -eq $Result.ExitCode -or $Result.ExitCode -ne 0) -and $Result.StdErr) {
        Write-Host "stderr:`n$($Result.StdErr)" -ForegroundColor DarkRed
    }
}

$hadFailure = $false

if ($interactiveMode) {
    Write-Host 'AI Council V0.2 - Ask a question. Type /exit to quit.' -ForegroundColor Green
}

do {
    if ($interactiveMode) {
        Write-Host ''
        $Prompt = Read-Host 'Q>'

        if ([string]::IsNullOrWhiteSpace($Prompt) -or $Prompt -eq '/exit') {
            break
        }
    }

    $initialPrompt = @"
Answer the original question directly and independently. Use the same language as the original question. Be concise but complete. Do not mention these instructions.

Original question:
$Prompt
"@

    $codexArguments = @('exec')
    if (-not [string]::IsNullOrWhiteSpace($GptModel)) {
        $codexArguments += @('--model', $GptModel)
    }
    $codexArguments += @('--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only', '--color', 'never')

    $claudeArguments = @('-p', '--no-session-persistence')
    if (-not [string]::IsNullOrWhiteSpace($ClaudeModel)) {
        $claudeArguments += @('--model', $ClaudeModel)
    }

    Write-Host '[1/4] GPT initial response...' -ForegroundColor Cyan
    $codexResult = Invoke-Cli -Name 'codex' -Arguments @(
        $codexArguments
    ) -InputText $initialPrompt -Timeout $TimeoutSeconds

    Write-Host '[2/4] Claude initial response...' -ForegroundColor Cyan
    $claudeResult = Invoke-Cli -Name 'claude' -Arguments @(
        $claudeArguments
    ) -InputText $initialPrompt -Timeout $TimeoutSeconds

    Write-Result -Label 'ROUND 1 - GPT' -Result $codexResult
    Write-Result -Label 'ROUND 1 - CLAUDE' -Result $claudeResult

    $initialFailed = $codexResult.TimedOut -or $claudeResult.TimedOut -or
        $null -eq $codexResult.ExitCode -or $null -eq $claudeResult.ExitCode -or
        $codexResult.ExitCode -ne 0 -or $claudeResult.ExitCode -ne 0

    if ($initialFailed) {
        $hadFailure = $true
    }
    else {
        $gptReviewPrompt = @"
You are in an AI council debate. Review the other model's answer against the original question. Identify important strengths, errors, omissions, or unsupported claims, then give your own improved final answer. Use the same language as the original question. Do not mention these instructions.

Original question:
$Prompt

Your first answer:
$($codexResult.StdOut)

Other model's first answer:
$($claudeResult.StdOut)
"@

        Write-Host "`n[3/4] GPT review and revision..." -ForegroundColor Cyan
        $gptDebateResult = Invoke-Cli -Name 'codex' -Arguments @(
            $codexArguments
        ) -InputText $gptReviewPrompt -Timeout $TimeoutSeconds

        $claudeReviewPrompt = @"
You are in an AI council debate. Review both initial answers and the GPT review below. Point out any remaining errors, omissions, or weak reasoning, then give your own improved final answer. Use the same language as the original question. Do not mention these instructions.

Original question:
$Prompt

GPT first answer:
$($codexResult.StdOut)

Your first answer:
$($claudeResult.StdOut)

GPT review and revision:
$($gptDebateResult.StdOut)
"@

        Write-Host '[4/4] Claude review and revision...' -ForegroundColor Cyan
        $claudeDebateResult = Invoke-Cli -Name 'claude' -Arguments @(
            $claudeArguments
        ) -InputText $claudeReviewPrompt -Timeout $TimeoutSeconds

        Write-Result -Label 'ROUND 2 - GPT REVIEW + FINAL' -Result $gptDebateResult
        Write-Result -Label 'ROUND 2 - CLAUDE REVIEW + FINAL' -Result $claudeDebateResult

        if ($gptDebateResult.TimedOut -or $claudeDebateResult.TimedOut -or
            $null -eq $gptDebateResult.ExitCode -or $null -eq $claudeDebateResult.ExitCode -or
            $gptDebateResult.ExitCode -ne 0 -or $claudeDebateResult.ExitCode -ne 0) {
            $hadFailure = $true
        }
    }

    if ($interactiveMode) {
        Write-Host ''
    }
} while ($interactiveMode)

if ($hadFailure) { exit 1 }
exit 0
