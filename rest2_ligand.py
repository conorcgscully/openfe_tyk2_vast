# Ligand-Only REST2 Conformational Sampling Recipe



import numpy as np
from openff.toolkit.topology import Molecule
from openff.interchange import Interchange
from openff.toolkit.typing.engines.smirnoff import ForceField
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen
import openmm as mm
from openmm import app, unit

# Load ligand
ligand_mol = Molecule.from_file('ligand.sdf')

# Analyze molecular properties
print(f"Molecular formula: {ligand_mol.to_rdkit().GetMolecularFormula()}")
print(f"Molecular weight: {Descriptors.MolWt(ligand_mol.to_rdkit()):.2f}")
print(f"Rotatable bonds: {Descriptors.NumRotatableBonds(ligand_mol.to_rdkit())}")
print(f"LogP: {Crippen.MolLogP(ligand_mol.to_rdkit()):.2f}")
print(f"Total atoms: {ligand_mol.n_atoms}")

# Generate multiple starting conformers for diversity
ligand_mol.generate_conformers(
    n_conformers=10,  # Generate multiple conformers
    rms_cutoff=0.5 * unit.angstrom,
    toolkit_registry=None
)

print(f"Generated {ligand_mol.n_conformers} conformers")

# Select the lowest energy conformer for starting structure
# (or use conformer selection based on energy minimization)
selected_conformer = 0  # Use first conformer

# Load OpenFF force field
openff_ff = ForceField('openff-2.1.0.offxml')  # Latest version

# Create topology and parameterize
ligand_topology = ligand_mol.to_topology()
ligand_interchange = Interchange.from_smirnoff(
    force_field=openff_ff,
    topology=ligand_topology
)

# Convert to OpenMM system
ligand_system = ligand_interchange.to_openmm()
ligand_omm_topology = ligand_interchange.topology.to_openmm()
ligand_positions = ligand_mol.conformers[selected_conformer].to_openmm()

print(f"System has {ligand_system.getNumForces()} force types")

from openmm.app import Modeller

# Create modeller with ligand
modeller = Modeller(ligand_omm_topology, ligand_positions)

# Add explicit solvent
# Choose solvent based on your needs
solvent_model = 'tip3p'  # or 'tip4pew', 'spce', etc.

modeller.addSolvent(
    app.ForceField('amber14/tip3pfb.xml'),  # Solvent force field
    model=solvent_model,
    padding=1.2*unit.nanometers,  # Generous padding for conformational freedom
    ionicStrength=0.15*unit.molar,  # Physiological ionic strength
    positiveIon='Na+',
    negativeIon='Cl-'
)

print(f"Solvated system has {modeller.topology.getNumAtoms()} total atoms")

# Save solvated structure
with open('ligand_solvated.pdb', 'w') as f:
    app.PDBFile.writeFile(modeller.topology, modeller.positions, f)

# Create force field for solvent
solvent_ff = app.ForceField('amber14/tip3pfb.xml')

# Create complete system with solvent
complete_system = solvent_ff.createSystem(
    modeller.topology,
    nonbondedMethod=app.PME,
    nonbondedCutoff=1.0*unit.nanometers,
    constraints=app.HBonds,
    rigidWater=True,
    ewaldErrorTolerance=0.0005
)

# Add ligand forces to complete system
for force in ligand_system.getForces():
    complete_system.addForce(force)

# Identify ligand atoms (first N atoms in topology)
ligand_atom_count = ligand_mol.n_atoms
ligand_atoms = list(range(ligand_atom_count))

print(f"Ligand atoms: {ligand_atoms}")

# Design temperature ladder for conformational sampling
n_replicas = 16  # More replicas for better mixing
min_temp = 300.0 * unit.kelvin  # Room temperature
max_temp = 500.0 * unit.kelvin  # Higher for conformational sampling

# Generate exponential temperature ladder
temperatures = []
for i in range(n_replicas):
    beta_min = 1.0 / (unit.BOLTZMANN_CONSTANT_kB * min_temp)
    beta_max = 1.0 / (unit.BOLTZMANN_CONSTANT_kB * max_temp)
    beta = beta_min + (beta_max - beta_min) * i / (n_replicas - 1)
    temp = 1.0 / (unit.BOLTZMANN_CONSTANT_kB * beta)
    temperatures.append(temp)

print(f"Temperature range: {min_temp} to {max_temp}")
print(f"Temperature ladder: {[f'{t:.1f}' for t in temperatures]}")

def apply_ligand_rest2_scaling(system, ligand_indices, beta_scale):
    """
    Apply REST2 scaling to ligand-only system
    beta_scale = beta_0/beta_m where beta_0 is reference state
    """
    
    # Scale factor for potential energy terms
    potential_scale = beta_scale
    
    for force_index in range(system.getNumForces()):
        force = system.getForce(force_index)
        
        # Scale bonded interactions within ligand
        if isinstance(force, mm.HarmonicBondForce):
            for bond_idx in range(force.getNumBonds()):
                p1, p2, length, k = force.getBondParameters(bond_idx)
                if p1 in ligand_indices and p2 in ligand_indices:
                    force.setBondParameters(bond_idx, p1, p2, length, k * potential_scale)
        
        # Scale angle interactions within ligand
        elif isinstance(force, mm.HarmonicAngleForce):
            for angle_idx in range(force.getNumAngles()):
                p1, p2, p3, angle, k = force.getAngleParameters(angle_idx)
                if all(p in ligand_indices for p in [p1, p2, p3]):
                    force.setAngleParameters(angle_idx, p1, p2, p3, angle, k * potential_scale)
        
        # Scale torsion interactions within ligand
        elif isinstance(force, mm.PeriodicTorsionForce):
            for torsion_idx in range(force.getNumTorsions()):
                p1, p2, p3, p4, periodicity, phase, k = force.getTorsionParameters(torsion_idx)
                if all(p in ligand_indices for p in [p1, p2, p3, p4]):
                    force.setTorsionParameters(torsion_idx, p1, p2, p3, p4, 
                                            periodicity, phase, k * potential_scale)
        
        # Scale nonbonded interactions involving ligand
        elif isinstance(force, mm.NonbondedForce):
            # Scale ligand-ligand interactions
            for i in ligand_indices:
                for j in range(i+1, len(ligand_indices)):
                    if j in ligand_indices:
                        # Get existing exception or create new one
                        try:
                            charge_prod, sigma, epsilon = force.getExceptionParameters(
                                force.getExceptionIndex(i, j))
                            force.setExceptionParameters(
                                force.getExceptionIndex(i, j), 
                                i, j, charge_prod * potential_scale, sigma, epsilon * potential_scale)
                        except:
                            # No existing exception, interactions handled by regular nonbonded
                            pass
            
            # Scale ligand charges and LJ parameters
            for atom_idx in ligand_indices:
                charge, sigma, epsilon = force.getParticleParameters(atom_idx)
                # Scale charge interactions with other ligand atoms and solvent
                force.setParticleParameters(atom_idx, charge * np.sqrt(potential_scale), 
                                          sigma, epsilon * potential_scale)

# Create scaled systems for each temperature
scaled_systems = []
for i, temp in enumerate(temperatures):
    # Create a copy of the system
    import copy
    system_copy = copy.deepcopy(complete_system)
    
    # Calculate scaling factor
    beta_ref = 1.0 / (unit.BOLTZMANN_CONSTANT_kB * temperatures[0])
    beta_i = 1.0 / (unit.BOLTZMANN_CONSTANT_kB * temp)
    beta_scale = beta_ref / beta_i
    
    # Apply REST2 scaling
    apply_ligand_rest2_scaling(system_copy, ligand_atoms, beta_scale)
    scaled_systems.append(system_copy)

from openmmtools.multistate import ReplicaExchangeSampler, MultiStateReporter
from openmmtools.states import ThermodynamicState, SamplerState
from openmmtools.mcmc import LangevinSplittingDynamicsMove

# Create thermodynamic states
thermodynamic_states = []
for i, (temp, system) in enumerate(zip(temperatures, scaled_systems)):
    state = ThermodynamicState(system=system, temperature=temp)
    thermodynamic_states.append(state)

# Create initial sampler state
sampler_state = SamplerState(positions=modeller.positions)

# Configure MCMC move
mcmc_move = LangevinSplittingDynamicsMove(
    timestep=2.0*unit.femtoseconds,
    collision_rate=1.0/unit.picosecond,
    n_steps=2500,  # 5 ps between exchange attempts
    reassign_velocities=True  # Important for temperature scaling
)

# Setup reporter
reporter = MultiStateReporter('ligand_rest2.nc', checkpoint_interval=500)

# Minimize each replica before starting
print("Minimizing structures...")
minimized_states = []

for i, state in enumerate(thermodynamic_states):
    context = mm.Context(state.system, mm.VerletIntegrator(1*unit.femtoseconds))
    context.setPositions(sampler_state.positions)
    
    # Minimize
    mm.LocalEnergyMinimizer.minimize(context, tolerance=10*unit.kilojoules_per_mole/unit.nanometers)
    
    # Store minimized positions
    minimized_positions = context.getState(getPositions=True).getPositions()
    minimized_states.append(SamplerState(positions=minimized_positions))
    
    del context
    
print("Minimization completed")

# Create and configure sampler
sampler = ReplicaExchangeSampler(
    mcmc_moves=mcmc_move,
    number_of_iterations=100000,  # 500 ns total simulation time
    online_analysis_interval=2000,  # Check convergence every 10 ns
    online_analysis_target_error=0.2,  # Target error for early stopping
)

# Initialize sampler
sampler.create(
    thermodynamic_states=thermodynamic_states,
    sampler_states=minimized_states,
    storage=reporter
)

print("Starting ligand REST2 simulation...")
print(f"Total simulation time: {sampler.number_of_iterations * mcmc_move.n_steps * mcmc_move.timestep}")

# Run simulation
sampler.run()
print("Simulation completed!")

import mdtraj as md
from openmmtools.multistate import MultiStateSamplerAnalyzer

# Load simulation data
analyzer = MultiStateSamplerAnalyzer('ligand_rest2.nc')

# Extract ground state trajectory
print("Extracting trajectories...")
ground_state_indices = analyzer.read_replica_thermodynamic_state(replica_index=0)
ground_state_positions = analyzer.read_sampler_states(replica_index=0)

# Convert to MDTraj
topology = md.Topology.from_openmm(modeller.topology)
positions_array = np.array([state.positions.value_in_unit(unit.nanometers) 
                           for state in ground_state_positions[::10]])  # Every 10th frame

traj = md.Trajectory(positions_array, topology)
print(f"Trajectory has {len(traj)} frames")

# Save trajectory
traj.save('ligand_conformations.xtc')
traj[0].save('ligand_topology.pdb')

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Select only ligand atoms for analysis
ligand_traj = traj.atom_slice(ligand_atoms)

# Calculate pairwise RMSD matrix
print("Calculating RMSD matrix...")
rmsd_matrix = np.empty((len(ligand_traj), len(ligand_traj)))
for i in range(len(ligand_traj)):
    rmsd_matrix[i] = md.rmsd(ligand_traj, ligand_traj, i)

# Perform clustering
n_clusters_range = range(2, 11)
silhouette_scores = []

for n_clusters in n_clusters_range:
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(rmsd_matrix)
    silhouette_avg = silhouette_score(rmsd_matrix, cluster_labels)
    silhouette_scores.append(silhouette_avg)
    
# Find optimal number of clusters
optimal_clusters = n_clusters_range[np.argmax(silhouette_scores)]
print(f"Optimal number of clusters: {optimal_clusters}")

# Final clustering
final_kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
cluster_labels = final_kmeans.fit_predict(rmsd_matrix)

# Extract representative conformers
representative_frames = []
for cluster_id in range(optimal_clusters):
    cluster_indices = np.where(cluster_labels == cluster_id)[0]
    # Find most central conformer in each cluster
    cluster_rmsd = rmsd_matrix[np.ix_(cluster_indices, cluster_indices)]
    central_idx = cluster_indices[np.argmin(cluster_rmsd.sum(axis=1))]
    representative_frames.append(central_idx)
    
print(f"Representative conformers: {representative_frames}")

# Define important dihedral angles (rotatable bonds)
def find_rotatable_dihedrals(molecule):
    """Find rotatable dihedral angles in molecule"""
    from rdkit import Chem
    
    mol = molecule.to_rdkit()
    rotatable_bonds = []
    
    for bond in mol.GetBonds():
        if bond.GetIsRotatableBond():
            begin_atom = bond.GetBeginAtom()
            end_atom = bond.GetEndAtom()
            
            # Find atoms connected to rotatable bond for dihedral definition
            begin_neighbors = [n.GetIdx() for n in begin_atom.GetNeighbors() 
                             if n.GetIdx() != end_atom.GetIdx()]
            end_neighbors = [n.GetIdx() for n in end_atom.GetNeighbors() 
                           if n.GetIdx() != begin_atom.GetIdx()]
            
            if begin_neighbors and end_neighbors:
                dihedral = [begin_neighbors[0], begin_atom.GetIdx(), 
                           end_atom.GetIdx(), end_neighbors[0]]
                rotatable_bonds.append(dihedral)
    
    return rotatable_bonds

# Get rotatable dihedrals
rotatable_dihedrals = find_rotatable_dihedrals(ligand_mol)
print(f"Found {len(rotatable_dihedrals)} rotatable dihedrals")

# Calculate dihedral angles over trajectory
dihedral_angles = {}
for i, dihedral in enumerate(rotatable_dihedrals):
    angles = md.compute_dihedrals(ligand_traj, [dihedral])
    dihedral_angles[f'Dihedral_{i+1}'] = angles.flatten()

import matplotlib.pyplot as plt
import seaborn as sns

# Plot dihedral free energy surfaces
if len(rotatable_dihedrals) >= 2:
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 2D histogram for first two dihedrals
    angles1 = dihedral_angles['Dihedral_1']
    angles2 = dihedral_angles['Dihedral_2']
    
    # Convert to degrees
    angles1_deg = np.degrees(angles1)
    angles2_deg = np.degrees(angles2)
    
    # Create 2D histogram
    H, xedges, yedges = np.histogram2d(angles1_deg, angles2_deg, bins=50)
    H_smooth = H + 1  # Add pseudocount
    free_energy = -np.log(H_smooth)
    free_energy = free_energy - np.min(free_energy)  # Set minimum to 0
    
    # Plot free energy surface
    X, Y = np.meshgrid(xedges[:-1], yedges[:-1])
    im = axes[0,0].contourf(X, Y, free_energy.T, levels=20, cmap='viridis')
    axes[0,0].set_xlabel('Dihedral 1 (degrees)')
    axes[0,0].set_ylabel('Dihedral 2 (degrees)')
    axes[0,0].set_title('Free Energy Surface')
    plt.colorbar(im, ax=axes[0,0], label='Free Energy (kT)')
    
    # Plot individual dihedral distributions
    axes[0,1].hist(angles1_deg, bins=50, alpha=0.7, density=True)
    axes[0,1].set_xlabel('Dihedral 1 (degrees)')
    axes[0,1].set_ylabel('Probability Density')
    axes[0,1].set_title('Dihedral 1 Distribution')
    
    axes[1,0].hist(angles2_deg, bins=50, alpha=0.7, density=True, color='orange')
    axes[1,0].set_xlabel('Dihedral 2 (degrees)')
    axes[1,0].set_ylabel('Probability Density')
    axes[1,0].set_title('Dihedral 2 Distribution')
    
    # RMSD distribution
    rmsd_self = md.rmsd(ligand_traj, ligand_traj, 0)
    axes[1,1].hist(rmsd_self, bins=50, alpha=0.7, color='green', density=True)
    axes[1,1].set_xlabel('RMSD from initial (nm)')
    axes[1,1].set_ylabel('Probability Density')
    axes[1,1].set_title('Conformational RMSD Distribution')
    
    plt.tight_layout()
    plt.savefig('conformational_analysis.png', dpi=300)
    plt.show()

# Save representative conformers from each cluster
representative_traj = ligand_traj[representative_frames]

for i, frame_idx in enumerate(representative_frames):
    conformer_traj = ligand_traj[frame_idx]
    conformer_traj.save(f'conformer_cluster_{i+1}.pdb')
    
print(f"Saved {len(representative_frames)} representative conformers")

# Calculate cluster populations
cluster_populations = []
for cluster_id in range(optimal_clusters):
    population = np.sum(cluster_labels == cluster_id) / len(cluster_labels)
    cluster_populations.append(population)
    print(f"Cluster {cluster_id + 1}: {population:.2%} of conformations")

# Analyze replica exchange efficiency
replica_states = analyzer.read_replica_thermodynamic_states()

plt.figure(figsize=(12, 8))
for replica in range(min(8, n_replicas)):  # Plot first 8 replicas
    plt.plot(replica_states[:, replica], alpha=0.7, label=f'Replica {replica}')

plt.xlabel('Iteration')
plt.ylabel('Temperature State Index')
plt.title('REST2 Replica Exchange Efficiency')
plt.legend()
plt.savefig('rest2_exchange_pattern.png', dpi=300)
plt.show()

# Calculate exchange acceptance rates
n_accepted = 0
n_total = 0
for i in range(len(replica_states) - 1):
    for j in range(n_replicas - 1):
        if replica_states[i, j] != replica_states[i+1, j]:
            n_accepted += 1
        n_total += 1

acceptance_rate = n_accepted / n_total if n_total > 0 else 0
print(f"Overall exchange acceptance rate: {acceptance_rate:.2%}")

# Check trajectory convergence
def calculate_convergence(trajectory, window_size=1000):
    """Calculate RMSD convergence over trajectory windows"""
    n_frames = len(trajectory)
    n_windows = n_frames // window_size
    
    convergence_rmsd = []
    reference_structure = trajectory[0]
    
    for i in range(n_windows):
        start_idx = i * window_size
        end_idx = min((i + 1) * window_size, n_frames)
        window_traj = trajectory[start_idx:end_idx]
        
        # Calculate average RMSD to reference in this window
        rmsd_values = md.rmsd(window_traj, reference_structure)
        avg_rmsd = np.mean(rmsd_values)
        convergence_rmsd.append(avg_rmsd)
    
    return convergence_rmsd

convergence_data = calculate_convergence(ligand_traj)

plt.figure(figsize=(10, 6))
plt.plot(convergence_data, 'o-')
plt.xlabel('Trajectory Window')
plt.ylabel('Average RMSD to Initial Structure (nm)')
plt.title('Conformational Sampling Convergence')
plt.savefig('convergence_analysis.png', dpi=300)
plt.show()


def generate_summary_report():
    """Generate a summary report of the conformational analysis"""
    
    report = f"""
    LIGAND CONFORMATIONAL SAMPLING SUMMARY
    =====================================
    
    Molecule Information:
    - Formula: {ligand_mol.to_rdkit().GetMolecularFormula()}
    - Molecular Weight: {Descriptors.MolWt(ligand_mol.to_rdkit()):.2f} Da
    - Rotatable Bonds: {len(rotatable_dihedrals)}
    - Total Atoms: {ligand_mol.n_atoms}
    
    Simulation Parameters:
    - Temperature Range: {min_temp:.1f} - {max_temp:.1f} K
    - Number of Replicas: {n_replicas}
    - Total Simulation Time: {sampler.number_of_iterations * mcmc_move.n_steps * mcmc_move.timestep}
    - Exchange Acceptance Rate: {acceptance_rate:.2%}
    
    Conformational Analysis:
    - Total Conformations Sampled: {len(ligand_traj)}
    - Optimal Number of Clusters: {optimal_clusters}
    - RMSD Range: {np.min(rmsd_self):.3f} - {np.max(rmsd_self):.3f} nm
    
    Cluster Populations:
    """
    
    for i, pop in enumerate(cluster_populations):
        report += f"    - Cluster {i+1}: {pop:.1%}\n"
    
    print(report)
    
    # Save report to file
    with open('conformational_analysis_summary.txt', 'w') as f:
        f.write(report)

# Generate summary
generate_summary_report()
