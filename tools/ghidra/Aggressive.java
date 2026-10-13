// Pre-analysis: enable aggressive code discovery for the section-less PS2 ELF.
import ghidra.app.script.GhidraScript;

public class Aggressive extends GhidraScript {
    @Override
    public void run() throws Exception {
        setAnalysisOption(currentProgram, "Aggressive Instruction Finder", "true");
        setAnalysisOption(currentProgram, "MIPS Constant Reference Analyzer", "true");
    }
}
