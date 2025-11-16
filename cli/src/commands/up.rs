use crate::docker::compose::DockerCompose;
use crate::docker::health::HealthChecker;
use crate::error::Result;
use colored::*;
use indicatif::{ProgressBar, ProgressStyle};

pub async fn execute(backend: String, fresh: bool) -> Result<()> {
    println!("{}", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".cyan());
    println!("{}", "  ZecKit - Starting Devnet".cyan().bold());
    println!("{}", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".cyan());
    println!();
    
    let compose = DockerCompose::new()?;
    
    // Fresh start if requested
    if fresh {
        println!("{}", "🧹 Cleaning up old data...".yellow());
        compose.down(true)?;
    }
    
    // Determine services to start
    let services = match backend.as_str() {
        "lwd" => vec!["zebra", "faucet", "lightwalletd"],
        "zaino" => vec!["zebra", "faucet", "zaino"],
        _ => vec!["zebra", "faucet"],
    };
    
    println!("{} Starting services: {}", "🚀".green(), services.join(", "));
    compose.up(&services)?;
    
    // Health checks with progress
    let pb = ProgressBar::new_spinner();
    pb.set_style(
        ProgressStyle::default_spinner()
            .template("{spinner:.green} {msg}")
            .unwrap()
    );
    
    pb.set_message("Waiting for Zebra...");
    let checker = HealthChecker::new();
    checker.wait_for_zebra(&pb).await?;
    
    pb.set_message("Waiting for Faucet...");
    checker.wait_for_faucet(&pb).await?;
    
    if backend != "none" {
        pb.set_message(format!("Waiting for {}...", backend));
        checker.wait_for_backend(&backend, &pb).await?;
    }
    
    pb.finish_with_message("✓ All services ready!".green().to_string());
    
    // Display connection info
    print_connection_info(&backend);
    
    Ok(())
}

fn print_connection_info(backend: &str) {
    println!();
    println!("{}", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".cyan());
    println!("{}", "  Services Ready".green().bold());
    println!("{}", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".cyan());
    println!();
    println!("  {} {}", "Zebra RPC:".bold(), "http://127.0.0.1:8232");
    println!("  {} {}", "Faucet API:".bold(), "http://127.0.0.1:8080");
    
    if backend == "lwd" {
        println!("  {} {}", "LightwalletD:".bold(), "http://127.0.0.1:9067");
    } else if backend == "zaino" {
        println!("  {} {}", "Zaino:".bold(), "http://127.0.0.1:9067 (experimental)");
    }
    
    println!();
    println!("{}", "Next steps:".bold());
    println!("  • Test faucet: curl http://127.0.0.1:8080/stats");
    println!("  • Run tests: zecdev test");
    println!("  • Check status: zecdev status");
    println!();
}