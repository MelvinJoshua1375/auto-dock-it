import * as vscode from "vscode";
import { spawn } from "child_process";

function autodockBin(): string {
  const cfg = vscode.workspace.getConfiguration("autodock");
  return cfg.get<string>("binPath") ?? "autodock";
}

function runAutodock(args: string[], title: string): Thenable<void> {
  return vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title, cancellable: true },
    (_progress, token) =>
      new Promise<void>((resolve, reject) => {
        const out = vscode.window.createOutputChannel("Auto-Dock It");
        out.show(true);
        out.appendLine(`$ ${autodockBin()} ${args.join(" ")}`);
        const proc = spawn(autodockBin(), args, { cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath });
        token.onCancellationRequested(() => proc.kill());
        proc.stdout.on("data", (b) => out.append(b.toString()));
        proc.stderr.on("data", (b) => out.append(b.toString()));
        proc.on("exit", (code) => {
          out.appendLine(`\nexit ${code}`);
          if (code === 0) {
            resolve();
          } else {
            reject(new Error(`autodock exited ${code}`));
          }
        });
      })
  );
}

export function activate(ctx: vscode.ExtensionContext) {
  ctx.subscriptions.push(
    vscode.commands.registerCommand("autodock.containerize", async () => {
      const ws = vscode.workspace.workspaceFolders?.[0];
      if (!ws) {
        vscode.window.showErrorMessage("Open a workspace first.");
        return;
      }
      await runAutodock(["run", ws.uri.fsPath], "Auto-Dock: containerizing workspace");
    }),

    vscode.commands.registerCommand("autodock.explain", async (uri?: vscode.Uri) => {
      const target = uri ?? vscode.window.activeTextEditor?.document.uri;
      if (!target) {
        vscode.window.showErrorMessage("Open a Dockerfile first.");
        return;
      }
      await runAutodock(["explain", target.fsPath], "Auto-Dock: explaining Dockerfile");
    }),

    vscode.commands.registerCommand("autodock.improve", async (uri?: vscode.Uri) => {
      const target = uri ?? vscode.window.activeTextEditor?.document.uri;
      if (!target) {
        vscode.window.showErrorMessage("Open a Dockerfile first.");
        return;
      }
      await runAutodock(["improve", target.fsPath], "Auto-Dock: reviewing Dockerfile");
    })
  );
}

export function deactivate() {}
