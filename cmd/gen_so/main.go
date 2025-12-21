package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"text/template"
)

const mainTmpl = `package main

import (
	"C"
	"unsafe"

	"github.com/jelech/rl_env_engine/pybridge"
	pkg "{{.PkgPath}}"
)

func init() {
	// Register the scenario
	// Assuming New{{.ScenarioName}}Scenario exists and returns core.Scenario
	pybridge.Register(pkg.New{{.ScenarioName}}Scenario())
}

//export CreateEnv
func CreateEnv(name *C.char, cfg *C.char) C.int {
	return C.int(pybridge.CreateEnv(C.GoString(name), C.GoString(cfg)))
}

//export Reset
func Reset(id C.int) C.int {
	return C.int(pybridge.Reset(int(id)))
}

//export Step
func Step(id C.int, action *C.double, len C.int) C.int {
	// Convert C array to Go slice
	// Note: This creates a slice header pointing to C memory. 
	// We copy data out in pybridge usually, but here we read.
	
	// Create a slice backed by C memory
	var acts []float64
	if len > 0 {
		// Slice header manipulation or using Go 1.21+ unsafe.Slice
		// For compatibility, let's do manual copy or unsafe cast
		// unsafe.Slice requires Go 1.17+
		acts = unsafe.Slice((*float64)(action), int(len))
	}
	
	return C.int(pybridge.Step(int(id), acts))
}

//export GetObservation
func GetObservation(id C.int, dest *C.double, maxLen C.int) C.int {
	return C.int(pybridge.GetObservation(int(id), unsafe.Pointer(dest), int(maxLen)))
}

//export GetReward
func GetReward(id C.int, dest *C.double, maxLen C.int) C.int {
	return C.int(pybridge.GetReward(int(id), unsafe.Pointer(dest), int(maxLen)))
}

//export GetDone
func GetDone(id C.int, dest *C.char, maxLen C.int) C.int {
	return C.int(pybridge.GetDone(int(id), unsafe.Pointer(dest), int(maxLen)))
}

//export CloseEnv
func CloseEnv(id C.int) {
	pybridge.CloseEnv(int(id))
}

func main() {}
`

type Config struct {
	PkgPath      string
	ScenarioName string
}

func main() {
	pkgPath := flag.String("pkg", "", "Go package path containing the scenario (e.g. git.garena.com/.../cache_rl)")
	scenarioName := flag.String("name", "", "Name of the Scenario (e.g. CacheRL -> NewCacheRLScenario)")
	outDir := flag.String("out", ".", "Output directory")
	flag.Parse()

	if *pkgPath == "" || *scenarioName == "" {
		fmt.Println("Usage: gen_so -pkg <package_path> -name <ScenarioName> [-out <dir>]")
		os.Exit(1)
	}

	// Ensure output directory exists
	if err := os.MkdirAll(*outDir, 0755); err != nil {
		fmt.Printf("Error creating output directory: %v\n", err)
		os.Exit(1)
	}

	f, err := os.Create(filepath.Join(*outDir, "main.go"))
	if err != nil {
		fmt.Printf("Error creating main.go: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()

	tmpl, err := template.New("main").Parse(mainTmpl)
	if err != nil {
		fmt.Printf("Error parsing template: %v\n", err)
		os.Exit(1)
	}

	err = tmpl.Execute(f, Config{
		PkgPath:      *pkgPath,
		ScenarioName: *scenarioName,
	})
	if err != nil {
		fmt.Printf("Error executing template: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Successfully generated main.go in %s\n", *outDir)
	fmt.Println("Build with: go build -buildmode=c-shared -o libenv.so " + *outDir)
}
