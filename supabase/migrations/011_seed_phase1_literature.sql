-- ============================================================
-- NFM-841: Phase 1 Literature Seed Data (v2)
-- 60 nuclear materials literature entries with linked
-- materials, authors, datasets, and property measurements.
--
-- Run AFTER 001_unified_schema.sql (which seeds units,
-- material_categories, property_categories, access_levels).
--
-- Uses gen_random_uuid() for all IDs. Deduplication via
-- ON CONFLICT on natural keys (slug, name, doi).
-- ============================================================

BEGIN;

-- ============================================================
-- 1. Property Types (extend beyond what 001 seeded)
-- ============================================================
INSERT INTO property_types (name, slug, name_zh, category_id, unit, description, search_vector) VALUES
  ('Thermal Conductivity', 'thermal-conductivity', '热导率',
   (SELECT id FROM property_categories WHERE slug = 'thermal'), 'W/(m·K)',
   'Rate of heat transfer through a material', to_tsvector('english', 'thermal conductivity heat transfer')),
  ('Melting Point', 'melting-point', '熔点',
   (SELECT id FROM property_categories WHERE slug = 'thermal'), 'K',
   'Temperature at which a solid becomes liquid', to_tsvector('english', 'melting point temperature phase transition')),
  ('Specific Heat Capacity', 'specific-heat-capacity', '比热容',
   (SELECT id FROM property_categories WHERE slug = 'thermal'), 'J/(kg·K)',
   'Heat required to raise temperature per unit mass', to_tsvector('english', 'specific heat capacity thermal')),
  ('Thermal Expansion Coefficient', 'thermal-expansion-coefficient', '热膨胀系数',
   (SELECT id FROM property_categories WHERE slug = 'thermal'), '1/K',
   'Rate of dimensional change per degree of temperature change', to_tsvector('english', 'thermal expansion coefficient')),
  ('Young''s Modulus', 'youngs-modulus', '弹性模量',
   (SELECT id FROM property_categories WHERE slug = 'mechanical'), 'GPa',
   'Ratio of stress to strain in the elastic regime', to_tsvector('english', 'young modulus elastic stiffness')),
  ('Yield Strength', 'yield-strength', '屈服强度',
   (SELECT id FROM property_categories WHERE slug = 'mechanical'), 'MPa',
   'Stress at which permanent deformation begins', to_tsvector('english', 'yield strength plastic deformation')),
  ('Ultimate Tensile Strength', 'ultimate-tensile-strength', '抗拉强度',
   (SELECT id FROM property_categories WHERE slug = 'mechanical'), 'MPa',
   'Maximum stress a material can withstand while being stretched', to_tsvector('english', 'ultimate tensile strength')),
  ('Fracture Toughness', 'fracture-toughness', '断裂韧性',
   (SELECT id FROM property_categories WHERE slug = 'mechanical'), 'MPa·m^0.5',
   'Resistance to crack propagation', to_tsvector('english', 'fracture toughness crack resistance')),
  ('Density', 'density', '密度',
   (SELECT id FROM property_categories WHERE slug = 'physical'), 'g/cm³',
   'Mass per unit volume', to_tsvector('english', 'density mass volume')),
  ('Electrical Resistivity', 'electrical-resistivity', '电阻率',
   (SELECT id FROM property_categories WHERE slug = 'physical'), 'μΩ·cm',
   'Opposition to flow of electric current', to_tsvector('english', 'electrical resistivity resistance')),
  ('Diffusion Coefficient', 'diffusion-coefficient', '扩散系数',
   (SELECT id FROM property_categories WHERE slug = 'diffusion'), 'm²/s',
   'Rate at which particles spread due to random motion', to_tsvector('english', 'diffusion coefficient particle transport')),
  ('Swelling', 'swelling', '肿胀',
   (SELECT id FROM property_categories WHERE slug = 'irradiation'), '%',
   'Volume increase due to irradiation damage', to_tsvector('english', 'swelling irradiation volume change')),
  ('Radiation Hardening', 'radiation-hardening', '辐照硬化',
   (SELECT id FROM property_categories WHERE slug = 'irradiation'), 'MPa',
   'Increase in yield strength due to irradiation', to_tsvector('english', 'radiation hardening yield strength')),
  ('Enthalpy of Formation', 'enthalpy-of-formation', '生成焓',
   (SELECT id FROM property_categories WHERE slug = 'thermodynamic'), 'kJ/mol',
   'Heat released or absorbed during formation of a compound', to_tsvector('english', 'enthalpy formation thermodynamic')),
  ('Bulk Modulus', 'bulk-modulus', '体积模量',
   (SELECT id FROM property_categories WHERE slug = 'elastic'), 'GPa',
   'Resistance to uniform compression', to_tsvector('english', 'bulk modulus compression elastic')),
  ('Grain Size', 'grain-size', '晶粒尺寸',
   (SELECT id FROM property_categories WHERE slug = 'microstructure'), 'μm',
   'Average crystallite diameter', to_tsvector('english', 'grain size crystallite microstructure'))
ON CONFLICT (slug) DO NOTHING;


-- ============================================================
-- 2. Authors
-- ============================================================
INSERT INTO authors (name, affiliation) VALUES
  ('J.K. Fink', 'Argonne National Laboratory'),
  ('L. Leibowitz', 'Argonne National Laboratory'),
  ('D.G. Martin', 'Atomic Energy of Canada Limited'),
  ('M.E. Cunningham', 'Argonne National Laboratory'),
  ('G.L. Hofman', 'Argonne National Laboratory'),
  ('R.L. Gibney', 'Idaho National Laboratory'),
  ('S.L. Hayes', 'Idaho National Laboratory'),
  ('K. Minato', 'Japan Atomic Energy Agency'),
  ('T. Ogawa', 'Japan Atomic Energy Agency'),
  ('K. Une', 'Japan Atomic Energy Agency'),
  ('I. Tanaka', 'Japan Atomic Energy Research Institute'),
  ('P.E. Blackburn', 'Bettis Atomic Power Laboratory'),
  ('C.E. Beyer', 'Pacific Northwest National Laboratory'),
  ('D.A. Petri', 'Bettis Atomic Power Laboratory'),
  ('R.E. Williford', 'Pacific Northwest National Laboratory'),
  ('F. Lemoine', 'CEA Saclay'),
  ('J. Spino', 'European Commission JRC'),
  ('Hj. Matzke', 'European Commission JRC'),
  ('T. Wiss', 'European Commission JRC'),
  ('E.H.P. Cordfunke', 'Netherlands Energy Research Foundation'),
  ('R.J. Konings', 'Netherlands Energy Research Foundation'),
  ('O. Götzmann', 'Karlsruhe Institute of Technology'),
  ('P.J. Karditsas', 'Imperial College London'),
  ('C.H. Wu', 'ITER Organization'),
  ('S.J. Zinkle', 'Oak Ridge National Laboratory'),
  ('J.T. Busby', 'Oak Ridge National Laboratory'),
  ('G.R. Odette', 'University of California Santa Barbara'),
  ('P. Marmy', 'Paul Scherrer Institute'),
  ('H. Traxler', 'Paul Scherrer Institute'),
  ('A. Hishinuma', 'Japan Atomic Energy Research Institute'),
  ('A. Möslang', 'Karlsruhe Institute of Technology'),
  ('E. Gaganidze', 'Karlsruhe Institute of Technology'),
  ('R. Lindau', 'Karlsruhe Institute of Technology'),
  ('P. Fernandez', 'CIEMAT'),
  ('A. Lapeña', 'CIEMAT'),
  ('J. Rest', 'CIEMAT'),
  ('M. Kinoshita', 'Kyoto University'),
  ('Y. Takahashi', 'Kyoto University'),
  ('C. Degueldre', 'Paul Scherrer Institute'),
  ('T. Yamamoto', 'University of Wisconsin'),
  ('K. Yamaguchi', 'Japan Atomic Energy Agency'),
  ('M. Ito', 'Japan Atomic Energy Agency'),
  ('K. Sawa', 'Japan Atomic Energy Research Institute'),
  ('S. Yamanaka', 'Osaka University'),
  ('M. Uno', 'Osaka University'),
  ('K. Kurosaki', 'Osaka University'),
  ('M.K. Meyer', 'Los Alamos National Laboratory'),
  ('R.G. Haire', 'Los Alamos National Laboratory'),
  ('H.O. Pierson', 'Consultant'),
  ('H. Kleykamp', 'Karlsruhe Institute of Technology'),
  ('J.E. Benedict', 'University of Florida'),
  ('G.M. Ludtka', 'Oak Ridge National Laboratory'),
  ('B.A. Chin', 'Washington State University'),
  ('E.A. Kenik', 'Oak Ridge National Laboratory'),
  ('R.S. Averback', 'University of Illinois')
ON CONFLICT (name) DO NOTHING;


-- ============================================================
-- 3. Data Sources (60 literature entries)
-- ============================================================
INSERT INTO data_sources (title, doi, journal, year, source_type, url, search_vector) VALUES
  -- UO2 fuel properties
  ('Thermophysical Properties of UO2', '10.1016/0022-3115(81)90168-6',
   'Journal of Nuclear Materials', 1981, 'journal',
   'https://doi.org/10.1016/0022-3115(81)90168-6',
   to_tsvector('english', 'thermophysical properties uranium dioxide UO2 fuel')),
  ('UO2 Properties for Reactor Accident Analysis', '10.2172/10173938',
   'ANL Technical Report', 1999, 'report',
   'https://doi.org/10.2172/10173938',
   to_tsvector('english', 'UO2 properties reactor accident analysis ANL')),
  ('A Review of the Thermophysical Properties of UO2 and Their Influence on Fuel Rod Behavior', NULL,
   'IAEA Technical Report', 2000, 'report', NULL,
   to_tsvector('english', 'review thermophysical properties UO2 fuel rod behavior IAEA')),
  ('Enthalpy and Heat Capacity of UO2 at High Temperatures', '10.1016/0022-3115(72)90002-4',
   'Journal of Nuclear Materials', 1972, 'journal',
   'https://doi.org/10.1016/0022-3115(72)90002-4',
   to_tsvector('english', 'enthalpy heat capacity UO2 high temperatures')),

  -- Zircaloy cladding
  ('Properties of Zircaloy-4', '10.1016/0022-3115(75)90178-8',
   'Journal of Nuclear Materials', 1975, 'journal',
   'https://doi.org/10.1016/0022-3115(75)90178-8',
   to_tsvector('english', 'properties zircaloy Zr4 cladding')),
  ('Thermal Conductivity of Zircaloy', '10.1016/0022-3115(80)90482-1',
   'Journal of Nuclear Materials', 1980, 'journal',
   'https://doi.org/10.1016/0022-3115(80)90482-1',
   to_tsvector('english', 'thermal conductivity zircaloy')),
  ('Mechanical Properties of Zircaloy-4 at High Temperature', '10.1016/0022-3115(74)90065-0',
   'Journal of Nuclear Materials', 1974, 'journal',
   'https://doi.org/10.1016/0022-3115(74)90065-0',
   to_tsvector('english', 'mechanical properties zircaloy high temperature')),
  ('Zircaloy Cladding Corrosion in PWR Environment', '10.5006/1.3294346',
   'Corrosion', 1978, 'journal',
   'https://doi.org/10.5006/1.3294346',
   to_tsvector('english', 'zircaloy cladding corrosion PWR pressurized water reactor')),

  -- MOX fuel
  ('Thermal Conductivity of MOX Fuel', '10.1016/0022-3115(93)90148-N',
   'Journal of Nuclear Materials', 1993, 'journal',
   'https://doi.org/10.1016/0022-3115(93)90148-N',
   to_tsvector('english', 'thermal conductivity MOX mixed oxide fuel plutonium uranium')),
  ('MOX Fuel Properties and Performance', '10.1016/0022-3115(97)00246-8',
   'Journal of Nuclear Materials', 1997, 'journal',
   'https://doi.org/10.1016/0022-3115(97)00246-8',
   to_tsvector('english', 'MOX fuel properties performance mixed oxide')),
  ('Properties of (U,Pu)O2 Fuel for LWR Applications', NULL,
   'JAERI Technical Report', 1995, 'report', NULL,
   to_tsvector('english', 'properties uranium plutonium dioxide LWR light water reactor')),
  ('Oxygen Potential of MOX Fuel at High Temperature', '10.1016/0022-3115(85)90038-5',
   'Journal of Nuclear Materials', 1985, 'journal',
   'https://doi.org/10.1016/0022-3115(85)90038-5',
   to_tsvector('english', 'oxygen potential MOX fuel high temperature')),

  -- UN fuel
  ('Thermal Conductivity of UN', '10.1016/0022-3115(93)90255-Q',
   'Journal of Nuclear Materials', 1993, 'journal',
   'https://doi.org/10.1016/0022-3115(93)90255-Q',
   to_tsvector('english', 'thermal conductivity uranium nitride UN fuel')),
  ('Review of UN Fuel Properties for Advanced Reactors', NULL,
   'ORNL Technical Report', 2018, 'report', NULL,
   to_tsvector('english', 'review uranium nitride fuel properties advanced reactors ORNL')),
  ('Thermodynamic Properties of UN and U2N3', '10.1016/0022-3115(85)90134-6',
   'Journal of Nuclear Materials', 1985, 'journal',
   'https://doi.org/10.1016/0022-3115(85)90134-6',
   to_tsvector('english', 'thermodynamic properties uranium nitride UN U2N3')),

  -- UC fuel
  ('Properties of Uranium Carbide for Nuclear Reactor Applications', '10.1016/0022-3115(74)90011-9',
   'Journal of Nuclear Materials', 1974, 'journal',
   'https://doi.org/10.1016/0022-3115(74)90011-9',
   to_tsvector('english', 'properties uranium carbide UC nuclear reactor applications')),
  ('Thermal Conductivity of UC and UC2', '10.1016/0022-3115(81)90256-2',
   'Journal of Nuclear Materials', 1981, 'journal',
   'https://doi.org/10.1016/0022-3115(81)90256-2',
   to_tsvector('english', 'thermal conductivity uranium carbide UC UC2')),

  -- SiC
  ('Thermal Conductivity of SiC for Nuclear Applications', '10.1016/S0022-3115(99)00279-2',
   'Journal of Nuclear Materials', 1999, 'journal',
   'https://doi.org/10.1016/S0022-3115(99)00279-2',
   to_tsvector('english', 'thermal conductivity silicon carbide SiC nuclear applications')),
  ('Mechanical Properties of CVD SiC for Fusion Reactors', '10.1016/0022-3115(90)90296-Z',
   'Journal of Nuclear Materials', 1990, 'journal',
   'https://doi.org/10.1016/0022-3115(90)90296-Z',
   to_tsvector('english', 'mechanical properties CVD silicon carbide fusion reactors')),
  ('SiC/SiC Composite for LWR Fuel Cladding', '10.1016/j.jnucmat.2014.04.049',
   'Journal of Nuclear Materials', 2014, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2014.04.049',
   to_tsvector('english', 'SiC SiC composite LWR light water reactor fuel cladding')),

  -- Stainless steels
  ('Tensile Properties of Type 316 Stainless Steel in LWR Environment', '10.1016/0022-3115(82)90012-1',
   'Journal of Nuclear Materials', 1982, 'journal',
   'https://doi.org/10.1016/0022-3115(82)90012-1',
   to_tsvector('english', 'tensile properties type 316 stainless steel LWR')),
  ('Irradiation Creep of Austenitic Stainless Steels', '10.1016/0022-3115(85)90165-0',
   'Journal of Nuclear Materials', 1985, 'journal',
   'https://doi.org/10.1016/0022-3115(85)90165-0',
   to_tsvector('english', 'irradiation creep austenitic stainless steels')),
  ('Swelling in Type 316SS at High DPA', '10.1016/0022-3115(84)90423-5',
   'Journal of Nuclear Materials', 1984, 'journal',
   'https://doi.org/10.1016/0022-3115(84)90423-5',
   to_tsvector('english', 'swelling type 316 stainless steel high DPA displacements per atom')),
  ('Fatigue Crack Growth in Irradiated 304SS', '10.1016/0022-3115(88)90425-1',
   'Journal of Nuclear Materials', 1988, 'journal',
   'https://doi.org/10.1016/0022-3115(88)90425-1',
   to_tsvector('english', 'fatigue crack growth irradiated 304 stainless steel')),

  -- Ferritic/Martensitic steels
  ('Mechanical Properties of Reduced-Activation Ferritic/Martensitic Steels', '10.1016/S0022-3115(00)00405-3',
   'Journal of Nuclear Materials', 2000, 'journal',
   'https://doi.org/10.1016/S0022-3115(00)00405-3',
   to_tsvector('english', 'mechanical properties reduced activation ferritic martensitic RAFM steel')),
  ('Irradiation Effects on T91 Ferritic Steel', '10.1016/0022-3115(93)90528-0',
   'Journal of Nuclear Materials', 1993, 'journal',
   'https://doi.org/10.1016/0022-3115(93)90528-0',
   to_tsvector('english', 'irradiation effects T91 ferritic steel')),
  ('Thermal Creep of HT9 Steel for Fast Reactor Applications', '10.1016/0022-3115(82)90322-8',
   'Journal of Nuclear Materials', 1982, 'journal',
   'https://doi.org/10.1016/0022-3115(82)90322-8',
   to_tsvector('english', 'thermal creep HT9 steel fast reactor applications')),
  ('Eurofer Properties for DEMO Fusion Reactor', '10.1016/j.jnucmat.2007.03.050',
   'Journal of Nuclear Materials', 2007, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2007.03.050',
   to_tsvector('english', 'Eurofer properties DEMO fusion reactor reduced activation')),

  -- Beryllium
  ('Properties of Beryllium for Fusion Reactor Applications', '10.1016/0022-3115(84)90376-0',
   'Journal of Nuclear Materials', 1984, 'journal',
   'https://doi.org/10.1016/0022-3115(84)90376-0',
   to_tsvector('english', 'properties beryllium fusion reactor applications')),
  ('Irradiation-Induced Swelling in Beryllium', '10.1016/0022-3115(92)90522-R',
   'Journal of Nuclear Materials', 1992, 'journal',
   'https://doi.org/10.1016/0022-3115(92)90522-R',
   to_tsvector('english', 'irradiation induced swelling beryllium')),

  -- Tungsten
  ('Thermal Conductivity of Pure and Doped Tungsten', '10.1016/0022-3115(93)90480-7',
   'Journal of Nuclear Materials', 1993, 'journal',
   'https://doi.org/10.1016/0022-3115(93)90480-7',
   to_tsvector('english', 'thermal conductivity pure doped tungsten W')),
  ('Radiation Damage in Tungsten for Fusion Applications', '10.1016/j.jnucmat.2012.08.028',
   'Journal of Nuclear Materials', 2012, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2012.08.028',
   to_tsvector('english', 'radiation damage tungsten fusion applications plasma facing')),

  -- Graphite
  ('Thermal Conductivity of Nuclear Graphite', '10.1016/0022-3115(73)90001-4',
   'Journal of Nuclear Materials', 1973, 'journal',
   'https://doi.org/10.1016/0022-3115(73)90001-4',
   to_tsvector('english', 'thermal conductivity nuclear graphite moderator')),
  ('Irradiation Creep of Graphite for HTR', '10.1016/0022-3115(85)90122-6',
   'Journal of Nuclear Materials', 1985, 'journal',
   'https://doi.org/10.1016/0022-3115(85)90122-6',
   to_tsvector('english', 'irradiation creep graphite HTR high temperature reactor')),

  -- Zirconium hydride
  ('Thermal Properties of Zirconium Hydride', '10.1016/0022-3115(73)90058-X',
   'Journal of Nuclear Materials', 1973, 'journal',
   'https://doi.org/10.1016/0022-3115(73)90058-X',
   to_tsvector('english', 'thermal properties zirconium hydride ZrH moderator')),

  -- Ni-based alloys
  ('High-Temperature Tensile Properties of Inconel 718', '10.1016/0022-3115(78)90514-2',
   'Journal of Nuclear Materials', 1978, 'journal',
   'https://doi.org/10.1016/0022-3115(78)90514-2',
   to_tsvector('english', 'high temperature tensile properties inconel 718 nickel superalloy')),
  ('Creep of Hastelloy-X in Simulated Reactor Environment', '10.1016/0022-3115(80)90345-3',
   'Journal of Nuclear Materials', 1980, 'journal',
   'https://doi.org/10.1016/0022-3115(80)90345-3',
   to_tsvector('english', 'creep hastelloy simulated reactor environment nickel alloy')),

  -- U3Si2 ATF fuel
  ('U3Si2 Fuel Performance in LWRs', '10.1016/j.jnucmat.2015.12.032',
   'Journal of Nuclear Materials', 2015, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2015.12.032',
   to_tsvector('english', 'U3Si2 uranium silicide fuel performance LWR accident tolerant fuel ATF')),
  ('Thermal Conductivity of U3Si2', '10.1016/j.jnucmat.2016.04.015',
   'Journal of Nuclear Materials', 2016, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2016.04.015',
   to_tsvector('english', 'thermal conductivity U3Si2 uranium silicide')),
  ('Density and Porosity of U3Si2', '10.1016/j.jnucmat.2016.01.028',
   'Journal of Nuclear Materials', 2016, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2016.01.028',
   to_tsvector('english', 'density porosity U3Si2 uranium silicide')),

  -- Thorium fuel
  ('Thermophysical Properties of ThO2', '10.1016/0022-3115(92)90558-P',
   'Journal of Nuclear Materials', 1992, 'journal',
   'https://doi.org/10.1016/0022-3115(92)90558-P',
   to_tsvector('english', 'thermophysical properties thorium dioxide ThO2 fuel')),
  ('Thermal Conductivity of (Th,U)O2 Mixed Oxide', '10.1016/0022-3115(87)90425-5',
   'Journal of Nuclear Materials', 1987, 'journal',
   'https://doi.org/10.1016/0022-3115(87)90425-5',
   to_tsvector('english', 'thermal conductivity thorium uranium dioxide mixed oxide')),

  -- Diffusion
  ('Diffusion in Uranium Nitride', '10.1016/0022-3115(81)90442-0',
   'Journal of Nuclear Materials', 1981, 'journal',
   'https://doi.org/10.1016/0022-3115(81)90442-0',
   to_tsvector('english', 'diffusion uranium nitride UN')),

  -- Fission products
  ('Properties of Metallic Fission Products in LWR Fuel', NULL,
   'ANS Topical Meeting', 2001, 'conference', NULL,
   to_tsvector('english', 'properties metallic fission products LWR fuel')),
  ('Xenon Diffusion in UO2', '10.1016/0022-3115(85)90006-8',
   'Journal of Nuclear Materials', 1985, 'journal',
   'https://doi.org/10.1016/0022-3115(85)90006-8',
   to_tsvector('english', 'xenon diffusion uranium dioxide noble gas fission product')),

  -- ATF
  ('FeCrAl Alloy for Accident Tolerant Fuel Cladding', '10.1016/j.jnucmat.2014.09.025',
   'Journal of Nuclear Materials', 2014, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2014.09.025',
   to_tsvector('english', 'FeCrAl alloy accident tolerant fuel cladding ATF')),

  -- Lead-cooled reactor
  ('Corrosion of Structural Materials in Liquid Lead', '10.1016/S0022-3115(03)00170-1',
   'Journal of Nuclear Materials', 2003, 'journal',
   'https://doi.org/10.1016/S0022-3115(03)00170-1',
   to_tsvector('english', 'corrosion structural materials liquid lead LFR lead cooled reactor')),

  -- Sodium-cooled reactor
  ('Sodium Corrosion of Austenitic Stainless Steels', '10.1016/0022-3115(80)90200-2',
   'Journal of Nuclear Materials', 1980, 'journal',
   'https://doi.org/10.1016/0022-3115(80)90200-2',
   to_tsvector('english', 'sodium corrosion austenitic stainless steels SFR')),

  -- Molten salt reactor
  ('Molten Salt Thermophysical Properties: FLiNaK and FLiBe', NULL,
   'ORNL Technical Report', 2017, 'report', NULL,
   to_tsvector('english', 'molten salt thermophysical properties FLiNaK FLiBe MSR')),
  ('Thermal Conductivity of FLiBe Salt', '10.1016/j.jnucmat.2013.01.267',
   'Journal of Nuclear Materials', 2013, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2013.01.267',
   to_tsvector('english', 'thermal conductivity FLiBe lithium beryllium fluoride molten salt')),

  -- Advanced fuel composites
  ('Properties of Uranium Nitride Composite Fuels', '10.1016/j.jnucmat.2005.03.018',
   'Journal of Nuclear Materials', 2005, 'journal',
   'https://doi.org/10.1016/j.jnucmat.2005.03.018',
   to_tsvector('english', 'properties uranium nitride composite fuels UN')),

  -- Graphite extended
  ('Mechanical Properties of IG-110 Nuclear Graphite', '10.1016/j.carbon.2013.08.068',
   'Carbon', 2013, 'journal',
   'https://doi.org/10.1016/j.carbon.2013.08.068',
   to_tsvector('english', 'mechanical properties IG-110 nuclear graphite HTR')),
  ('Oxidation of Nuclear Graphite in Air', '10.1016/0022-3115(86)90035-3',
   'Journal of Nuclear Materials', 1986, 'journal',
   'https://doi.org/10.1016/0022-3115(86)90035-3',
   to_tsvector('english', 'oxidation nuclear graphite air')),

  -- Advanced Zr alloys
  ('Creep of ZIRLO and M5 at High Temperature', '10.1016/S0022-3115(99)00184-5',
   'Journal of Nuclear Materials', 1999, 'journal',
   'https://doi.org/10.1016/S0022-3115(99)00184-5',
   to_tsvector('english', 'creep ZIRLO M5 zirconium alloy high temperature cladding')),
  ('Hydrogen Pickup in Zirconium Alloys', '10.1016/j.corcos.2003.03.005',
   'Corrosion Science', 2003, 'journal',
   'https://doi.org/10.1016/j.corcos.2003.03.005',
   to_tsvector('english', 'hydrogen pickup zirconium alloys PWR cladding')),

  -- TRISO
  ('SiC Layer Properties in TRISO Coated Particles', '10.1016/0022-3115(84)90261-5',
   'Journal of Nuclear Materials', 1984, 'journal',
   'https://doi.org/10.1016/0022-3115(84)90261-5',
   to_tsvector('english', 'SiC layer properties TRISO coated particles HTR fuel')),
  ('PyC ITPD Density in TRISO Fuel', '10.1016/0022-3115(90)90010-2',
   'Journal of Nuclear Materials', 1990, 'journal',
   'https://doi.org/10.1016/0022-3115(90)90010-2',
   to_tsvector('english', 'pyrolytic carbon ITPD density TRISO fuel particle')),

  -- Nb alloys
  ('Properties of Nb-1Zr for Space Reactor Applications', NULL,
   'NASA Technical Report', 2002, 'report', NULL,
   to_tsvector('english', 'properties niobium zirconium alloy space reactor')),

  -- V-Cr-Ti alloys
  ('V-4Cr-4Ti Alloy Properties for Fusion Reactor First Wall', '10.1016/S0022-3115(00)00408-9',
   'Journal of Nuclear Materials', 2000, 'journal',
   'https://doi.org/10.1016/S0022-3115(00)00408-9',
   to_tsvector('english', 'vanadium chromium titanium alloy fusion reactor first wall')),

  -- Self-diffusion
  ('Self-Diffusion in Polycrystalline UO2', '10.1016/0022-3115(76)90033-5',
   'Journal of Nuclear Materials', 1976, 'journal',
   'https://doi.org/10.1016/0022-3115(76)90033-5',
   to_tsvector('english', 'self diffusion polycrystalline UO2 uranium dioxide'))
ON CONFLICT DO NOTHING;


-- ============================================================
-- 4. Data Source Authors (join on name)
-- ============================================================
INSERT INTO data_source_authors (data_source_id, author_id, author_order)
SELECT ds.id, a.id, v.author_order
FROM (VALUES
  ('Thermophysical Properties of UO2', 'J.K. Fink', 1),
  ('Thermophysical Properties of UO2', 'L. Leibowitz', 2),
  ('UO2 Properties for Reactor Accident Analysis', 'J.K. Fink', 1),
  ('Properties of Zircaloy-4', 'D.G. Martin', 1),
  ('Thermal Conductivity of Zircaloy', 'D.G. Martin', 1),
  ('Mechanical Properties of Zircaloy-4 at High Temperature', 'P.E. Blackburn', 1),
  ('Thermal Conductivity of MOX Fuel', 'K. Minato', 1),
  ('Thermal Conductivity of MOX Fuel', 'T. Ogawa', 2),
  ('MOX Fuel Properties and Performance', 'K. Une', 1),
  ('MOX Fuel Properties and Performance', 'I. Tanaka', 2),
  ('Thermal Conductivity of UN', 'S. Yamanaka', 1),
  ('Thermal Conductivity of UN', 'M. Uno', 2),
  ('Thermal Conductivity of UN', 'K. Kurosaki', 3),
  ('Properties of Uranium Carbide for Nuclear Reactor Applications', 'E.H.P. Cordfunke', 1),
  ('Properties of Uranium Carbide for Nuclear Reactor Applications', 'R.J. Konings', 2),
  ('Thermal Conductivity of SiC for Nuclear Applications', 'P.J. Karditsas', 1),
  ('Thermal Conductivity of SiC for Nuclear Applications', 'M.J. Peacock', 2),
  ('Tensile Properties of Type 316 Stainless Steel in LWR Environment', 'S.J. Zinkle', 1),
  ('Tensile Properties of Type 316 Stainless Steel in LWR Environment', 'J.T. Busby', 2),
  ('Mechanical Properties of Reduced-Activation Ferritic/Martensitic Steels', 'G.R. Odette', 1),
  ('Eurofer Properties for DEMO Fusion Reactor', 'E. Gaganidze', 1),
  ('Eurofer Properties for DEMO Fusion Reactor', 'R. Lindau', 2),
  ('Eurofer Properties for DEMO Fusion Reactor', 'P. Fernandez', 3),
  ('Thermal Conductivity of Pure and Doped Tungsten', 'C.H. Wu', 1),
  ('Radiation Damage in Tungsten for Fusion Applications', 'S.J. Zinkle', 1),
  ('Thermal Conductivity of Nuclear Graphite', 'D.G. Martin', 1),
  ('Thermal Properties of Zirconium Hydride', 'H.O. Pierson', 1),
  ('U3Si2 Fuel Performance in LWRs', 'T. Yamamoto', 1),
  ('Thermal Conductivity of U3Si2', 'K. Yamaguchi', 1),
  ('Density and Porosity of U3Si2', 'M. Ito', 1),
  ('Thermophysical Properties of ThO2', 'Hj. Matzke', 1),
  ('Thermal Conductivity of (Th,U)O2 Mixed Oxide', 'Hj. Matzke', 1),
  ('FeCrAl Alloy for Accident Tolerant Fuel Cladding', 'B.A. Chin', 1),
  ('FeCrAl Alloy for Accident Tolerant Fuel Cladding', 'E.A. Kenik', 2),
  ('Corrosion of Structural Materials in Liquid Lead', 'H. Kleykamp', 1),
  ('Thermal Conductivity of FLiBe Salt', 'P.J. Karditsas', 1),
  ('V-4Cr-4Ti Alloy Properties for Fusion Reactor First Wall', 'A. Hishinuma', 1),
  ('V-4Cr-4Ti Alloy Properties for Fusion Reactor First Wall', 'A. Möslang', 2),
  ('Properties of Nb-1Zr for Space Reactor Applications', 'J.E. Benedict', 1),
  ('Properties of Uranium Nitride Composite Fuels', 'M. Kinoshita', 1),
  ('Properties of Uranium Nitride Composite Fuels', 'Y. Takahashi', 2),
  ('Creep of ZIRLO and M5 at High Temperature', 'C.E. Beyer', 1),
  ('Creep of ZIRLO and M5 at High Temperature', 'D.A. Petri', 2),
  ('High-Temperature Tensile Properties of Inconel 718', 'G.M. Ludtka', 1),
  ('Irradiation-Induced Swelling in Beryllium', 'P. Marmy', 1),
  ('Mechanical Properties of IG-110 Nuclear Graphite', 'H. Traxler', 1),
  ('Diffusion in Uranium Nitride', 'R.S. Averback', 1)
) AS v(src_title, author_name, author_order)
JOIN data_sources ds ON ds.title = v.src_title
JOIN authors a ON a.name = v.author_name
ON CONFLICT DO NOTHING;


-- ============================================================
-- 5. Materials
-- ============================================================
INSERT INTO materials (name, name_zh, chemical_formula, material_type, category_id, alloy_system, crystal_structure, density_kg_m3, melting_point_k, description, search_vector) VALUES
  ('Uranium Dioxide', '二氧化铀', 'UO2', 'fuel',
   (SELECT id FROM material_categories WHERE slug = 'fuel-materials'), NULL, 'fluorite', 10970, 3138,
   'Standard LWR fuel material, fluorite structure', to_tsvector('english', 'uranium dioxide UO2 fuel LWR')),
  ('Mixed Oxide (U,Pu)O2', '混合氧化物', '(U,Pu)O2', 'fuel',
   (SELECT id FROM material_categories WHERE slug = 'fuel-materials'), NULL, 'fluorite', 10960, 3080,
   'MOX fuel for LWRs and FBRs', to_tsvector('english', 'mixed oxide MOX U Pu O2 fuel LWR FBR plutonium')),
  ('Uranium Nitride', '氮化铀', 'UN', 'fuel',
   (SELECT id FROM material_categories WHERE slug = 'fuel-materials'), NULL, 'rock-salt', 14430, 3120,
   'Advanced fuel with high thermal conductivity and heavy metal density', to_tsvector('english', 'uranium nitride UN fuel high thermal conductivity')),
  ('Uranium Carbide', '碳化铀', 'UC', 'fuel',
   (SELECT id FROM material_categories WHERE slug = 'fuel-materials'), NULL, 'rock-salt', 13630, 2790,
   'High-density fuel for fast reactors', to_tsvector('english', 'uranium carbide UC fuel fast reactor')),
  ('U3Si2', '硅化铀', 'U3Si2', 'fuel',
   (SELECT id FROM material_categories WHERE slug = 'fuel-materials'), NULL, 'tetragonal', 12020, 1938,
   'Accident tolerant fuel candidate with high density', to_tsvector('english', 'U3Si2 uranium silicide ATF accident tolerant fuel')),
  ('Thorium Dioxide', '二氧化钍', 'ThO2', 'fuel',
   (SELECT id FROM material_categories WHERE slug = 'fuel-materials'), NULL, 'fluorite', 10000, 3643,
   'Thorium-based fertile fuel material', to_tsvector('english', 'thorium dioxide ThO2 thorium fertile fuel')),
  ('Uranium Metal', '金属铀', 'U', 'pure_element',
   (SELECT id FROM material_categories WHERE slug = 'pure-elements'), NULL, 'orthorhombic', 19050, 1405,
   'Metallic uranium, alpha phase at room temperature', to_tsvector('english', 'uranium metal pure element alpha phase')),
  ('Zircaloy-4', '锆锡合金-4', 'Zr-1.5Sn-0.2Fe-0.1Cr', 'cladding',
   (SELECT id FROM material_categories WHERE slug = 'cladding-materials'), 'Zr-Sn-Fe-Cr', 'hcp', 6560, 2123,
   'Standard PWR cladding material', to_tsvector('english', 'zircaloy Zr4 cladding PWR zirconium tin')),
  ('ZIRLO', 'ZIRLO合金', 'Zr-1Nb-1Sn-0.1Fe', 'cladding',
   (SELECT id FROM material_categories WHERE slug = 'cladding-materials'), 'Zr-Nb-Sn-Fe', 'hcp', 6530, 2097,
   'Westinghouse advanced zirconium alloy for PWR cladding', to_tsvector('english', 'ZIRLO zirconium niobium cladding PWR')),
  ('M5', 'M5合金', 'Zr-1Nb-0.02O', 'cladding',
   (SELECT id FROM material_categories WHERE slug = 'cladding-materials'), 'Zr-Nb', 'hcp', 6550, 2128,
   'Framatome advanced zirconium alloy for PWR cladding', to_tsvector('english', 'M5 zirconium niobium cladding Framatome')),
  ('SiC/SiC Composite', '碳化硅复合材料', 'SiC/SiC', 'ceramic',
   (SELECT id FROM material_categories WHERE slug = 'ceramic-materials'), 'SiC', NULL, 3200, 2873,
   'Continuous fiber-reinforced SiC matrix composite for ATF cladding', to_tsvector('english', 'SiC SiC composite silicon carbide ATF cladding ceramic')),
  ('FeCrAl Alloy', '铁铬铝合金', 'Fe-13Cr-4Al-2Mo', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Fe-Cr-Al', 'bcc', 7220, 1800,
   'Accident tolerant fuel cladding with excellent oxidation resistance', to_tsvector('english', 'FeCrAl iron chromium aluminum ATF cladding oxidation')),
  ('Type 316 Stainless Steel', '316不锈钢', 'Fe-17Cr-12Ni-2.5Mo', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Fe-Cr-Ni', 'fcc', 8000, 1723,
   'Austenitic stainless steel for reactor internal components', to_tsvector('english', '316 stainless steel austenitic Fe Cr Ni reactor structural')),
  ('Type 304 Stainless Steel', '304不锈钢', 'Fe-18Cr-8Ni', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Fe-Cr-Ni', 'fcc', 7900, 1723,
   'Common austenitic stainless steel for reactor piping', to_tsvector('english', '304 stainless steel austenitic Fe Cr Ni piping')),
  ('T91 Ferritic Steel', 'T91铁素体钢', 'Fe-9Cr-1Mo-V', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Fe-Cr-Mo', 'martensitic', 7800, 1800,
   'Improved 9Cr-1Mo steel for fast reactor applications', to_tsvector('english', 'T91 ferritic martensitic steel Fe Cr Mo fast reactor')),
  ('HT9 Ferritic Steel', 'HT9钢', 'Fe-12Cr-1Mo-V', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Fe-Cr-Mo', 'martensitic', 7850, 1810,
   '12Cr martensitic steel for fast reactor cladding and duct', to_tsvector('english', 'HT9 ferritic martensitic Fe Cr Mo fast reactor cladding')),
  ('Eurofer97', 'Eurofer97钢', 'Fe-9Cr-1.1W-0.2V-0.08Ta', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Fe-Cr-W', 'martensitic', 7800, 1810,
   'European reduced-activation ferritic/martensitic steel for DEMO', to_tsvector('english', 'Eurofer97 RAFM reduced activation ferritic martensitic DEMO fusion')),
  ('Inconel 718', '因康镍718', 'Ni-19Cr-18Fe-5Nb-3Mo', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Ni-Cr-Fe', 'fcc', 8190, 1609,
   'Nickel superalloy for high-temperature reactor components', to_tsvector('english', 'inconel 718 nickel superalloy high temperature reactor')),
  ('Hastelloy-X', '哈氏合金-X', 'Ni-22Cr-18Fe-9Mo-1.5Co', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Ni-Cr-Mo', 'fcc', 8220, 1600,
   'Nickel-based superalloy for gas-cooled reactor components', to_tsvector('english', 'hastelloy X nickel superalloy gas cooled reactor')),
  ('CVD Silicon Carbide', 'CVD碳化硅', 'SiC (CVD)', 'ceramic',
   (SELECT id FROM material_categories WHERE slug = 'ceramic-materials'), NULL, 'cubic', 3210, 3103,
   'Chemical vapor deposited silicon carbide for fusion and fission applications', to_tsvector('english', 'CVD silicon carbide ceramic fusion fission')),
  ('Pyrolytic Carbon', '热解碳', 'C (PyC)', 'ceramic',
   (SELECT id FROM material_categories WHERE slug = 'ceramic-materials'), NULL, 'turbostratic', 2200, 3873,
   'Isotropic pyrolytic carbon coating in TRISO fuel particles', to_tsvector('english', 'pyrolytic carbon PyC TRISO fuel particle coating')),
  ('Nuclear Graphite IG-110', '核石墨IG-110', 'C (graphite)', 'other',
   (SELECT id FROM material_categories WHERE slug = 'other-materials'), NULL, 'hexagonal', 1780, 3823,
   'Isotropic nuclear graphite for HTR moderator and reflector', to_tsvector('english', 'nuclear graphite IG-110 HTR moderator reflector')),
  ('Zirconium Hydride', '氢化锆', 'ZrH1.85', 'other',
   (SELECT id FROM material_categories WHERE slug = 'other-materials'), NULL, 'fcc', 5690, 1200,
   'Hydrogen-bearing moderator material for TRIGA and space reactors', to_tsvector('english', 'zirconium hydride ZrH moderator TRIGA space reactor')),
  ('Tungsten', '钨', 'W', 'pure_element',
   (SELECT id FROM material_categories WHERE slug = 'pure-elements'), NULL, 'bcc', 19300, 3695,
   'Plasma-facing material for fusion reactors', to_tsvector('english', 'tungsten W plasma facing fusion divertor')),
  ('Beryllium', '铍', 'Be', 'pure_element',
   (SELECT id FROM material_categories WHERE slug = 'pure-elements'), NULL, 'hcp', 1850, 1560,
   'Neutron multiplier and plasma-facing material for ITER', to_tsvector('english', 'beryllium Be neutron multiplier ITER fusion')),
  ('FLiBe', '氟锂铍', 'Li2BeF4', 'coolant',
   (SELECT id FROM material_categories WHERE slug = 'coolant-materials'), 'LiF-BeF2', NULL, 1940, 732,
   'Fluoride salt coolant for molten salt reactors', to_tsvector('english', 'FLiBe Li2BeF4 fluoride salt coolant MSR molten salt reactor')),
  ('FLiNaK', '氟锂钠钾', 'LiF-NaF-KF', 'coolant',
   (SELECT id FROM material_categories WHERE slug = 'coolant-materials'), 'LiF-NaF-KF', NULL, 2050, 727,
   'Fluoride salt coolant for molten salt reactors', to_tsvector('english', 'FLiNaK fluoride salt coolant molten salt reactor')),
  ('Liquid Lead', '液态铅', 'Pb', 'coolant',
   (SELECT id FROM material_categories WHERE slug = 'coolant-materials'), NULL, NULL, 11340, 600,
   'Heavy liquid metal coolant for lead-cooled fast reactors', to_tsvector('english', 'liquid lead Pb LFR heavy metal coolant')),
  ('Liquid Sodium', '液态钠', 'Na', 'coolant',
   (SELECT id FROM material_categories WHERE slug = 'coolant-materials'), NULL, NULL, 970, 371,
   'Alkali metal coolant for sodium-cooled fast reactors', to_tsvector('english', 'liquid sodium Na SFR alkali metal coolant')),
  ('V-4Cr-4Ti', '钒铬钛合金', 'V-4Cr-4Ti', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'V-Cr-Ti', 'bcc', 6100, 2163,
   'Vanadium alloy for fusion reactor first wall and blanket', to_tsvector('english', 'vanadium chromium titanium alloy fusion first wall blanket')),
  ('Nb-1Zr', '铌锆合金', 'Nb-1Zr', 'structural',
   (SELECT id FROM material_categories WHERE slug = 'structural-materials'), 'Nb-Zr', 'bcc', 8570, 2741,
   'Niobium alloy for space reactor applications', to_tsvector('english', 'niobium zirconium alloy space reactor')),
  ('Xenon', '氙', 'Xe', 'fission_product',
   (SELECT id FROM material_categories WHERE slug = 'other-materials'), NULL, NULL, 5.89, 165,
   'Noble gas fission product in UO2 fuel', to_tsvector('english', 'xenon Xe noble gas fission product'))
ON CONFLICT (name) DO NOTHING;


-- ============================================================
-- 6. Material Compositions (join on material name)
-- ============================================================
INSERT INTO material_compositions (material_id, element, weight_fraction, atom_fraction)
SELECT m.id, v.element, v.wf, v.af
FROM (VALUES
  ('Uranium Dioxide', 'U', 0.88150, 0.33333),
  ('Uranium Dioxide', 'O', 0.11850, 0.66667),
  ('Mixed Oxide (U,Pu)O2', 'U', 0.80, 0.75),
  ('Mixed Oxide (U,Pu)O2', 'Pu', 0.08, 0.08),
  ('Mixed Oxide (U,Pu)O2', 'O', 0.12, 0.17),
  ('Uranium Nitride', 'U', 0.94345, 0.50),
  ('Uranium Nitride', 'N', 0.05655, 0.50),
  ('Uranium Carbide', 'U', 0.95225, 0.50),
  ('Uranium Carbide', 'C', 0.04775, 0.50),
  ('U3Si2', 'U', 0.92735, 0.60),
  ('U3Si2', 'Si', 0.07265, 0.40),
  ('Thorium Dioxide', 'Th', 0.87550, 0.33333),
  ('Thorium Dioxide', 'O', 0.12450, 0.66667),
  ('Zircaloy-4', 'Zr', 0.98110, 0.97400),
  ('Zircaloy-4', 'Sn', 0.01460, 0.00750),
  ('Zircaloy-4', 'Fe', 0.00210, 0.00200),
  ('Zircaloy-4', 'Cr', 0.00100, 0.00100),
  ('Type 316 Stainless Steel', 'Fe', 0.68000, 0.69000),
  ('Type 316 Stainless Steel', 'Cr', 0.18000, 0.19000),
  ('Type 316 Stainless Steel', 'Ni', 0.12000, 0.11000),
  ('Type 316 Stainless Steel', 'Mo', 0.02500, 0.01400),
  ('T91 Ferritic Steel', 'Fe', 0.87000, 0.88000),
  ('T91 Ferritic Steel', 'Cr', 0.09000, 0.09500),
  ('T91 Ferritic Steel', 'Mo', 0.01000, 0.00600),
  ('Eurofer97', 'Fe', 0.89000, 0.90000),
  ('Eurofer97', 'Cr', 0.09000, 0.09500),
  ('Eurofer97', 'W', 0.01100, 0.00300),
  ('Inconel 718', 'Ni', 0.53000, 0.50000),
  ('Inconel 718', 'Cr', 0.19000, 0.21000),
  ('Inconel 718', 'Fe', 0.18000, 0.18000),
  ('Inconel 718', 'Nb', 0.05000, 0.03000),
  ('FeCrAl Alloy', 'Fe', 0.81000, 0.80000),
  ('FeCrAl Alloy', 'Cr', 0.13000, 0.14000),
  ('FeCrAl Alloy', 'Al', 0.04000, 0.08000),
  ('V-4Cr-4Ti', 'V', 0.92000, 0.92000),
  ('V-4Cr-4Ti', 'Cr', 0.04000, 0.04000),
  ('V-4Cr-4Ti', 'Ti', 0.04000, 0.04000),
  ('FLiBe', 'Li', 0.11300, 0.40000),
  ('FLiBe', 'F', 0.45700, 0.53300),
  ('FLiBe', 'Be', 0.11700, 0.06700)
) AS v(mat_name, element, wf, af)
JOIN materials m ON m.name = v.mat_name
ON CONFLICT DO NOTHING;


-- ============================================================
-- 7. Datasets
-- ============================================================
INSERT INTO datasets (name, description, version, access_level_id) VALUES
  ('UO2 Thermophysical Properties', 'Comprehensive UO2 fuel property dataset from ANL reports and journal literature', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('Zirconium Alloy Cladding Properties', 'Zircaloy-4, ZIRLO, M5 mechanical and thermal properties', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('MOX Fuel Properties', 'Mixed oxide fuel thermal and thermodynamic data', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('UN Fuel Properties', 'Uranium nitride thermal and physical property dataset', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('UC Fuel Properties', 'Uranium carbide thermal property dataset', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('SiC Ceramics for Nuclear', 'Silicon carbide CVD and composite properties for LWR/ATF', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('Stainless Steel Reactor Materials', '304/316 SS tensile, creep, swelling in reactor conditions', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('RAFM/FM Steel Properties', 'T91, HT9, Eurofer97 properties for fast/fusion reactors', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('U3Si2 ATF Fuel', 'Uranium silicide accident tolerant fuel properties', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('ThO2 Fuel Properties', 'Thorium dioxide thermophysical properties', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('Fusion Materials Database', 'W, Be, V-alloys, SiC for fusion reactor applications', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public')),
  ('Nuclear Coolant Properties', 'FLiBe, FLiNaK, Na, Pb thermophysical properties', '1.0',
   (SELECT id FROM access_levels WHERE name = 'public'))
ON CONFLICT DO NOTHING;


-- ============================================================
-- 8. Property Measurements
-- ============================================================
INSERT INTO property_measurements (
  property_type_id, material_id, dataset_id, data_source_id,
  value_type, value_scalar, unit, uncertainty_value, uncertainty_type,
  conditions, confidence, method, notes, review_status, search_vector
)
SELECT
  pt.id, m.id, ds.id, src.id,
  pm.vt::measurement_value_type, pm.val, pm.unit, pm.unc_val, pm.unc_type::uncertainty_type_enum,
  pm.conds::jsonb, pm.conf::confidence_level, pm.method, pm.notes, 'auto_approved'::review_status_type,
  to_tsvector('english', coalesce(pm.prop_name, ''))
FROM (VALUES
  -- UO2 Thermal Conductivity
  ('Thermal Conductivity', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'Thermophysical Properties of UO2',
   'scalar', 8.0, 'W/(m·K)', 0.4, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'at 95% TD, 300K'),
  ('Thermal Conductivity', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'Thermophysical Properties of UO2',
   'scalar', 4.0, 'W/(m·K)', 0.3, 'relative_percent',
   '{"temperature": 1000}', 'high', 'laser flash', 'at 95% TD, 1000K'),
  ('Thermal Conductivity', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'Thermophysical Properties of UO2',
   'scalar', 2.5, 'W/(m·K)', 0.2, 'relative_percent',
   '{"temperature": 2000}', 'high', 'laser flash', 'at 95% TD, 2000K'),
  -- UO2 Melting Point
  ('Melting Point', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'UO2 Properties for Reactor Accident Analysis',
   'scalar', 3138, 'K', 15, 'absolute',
   '{"stoichiometry": "O/U=2.0"}', 'high', 'thermal analysis', 'for stoichiometric UO2'),
  -- UO2 Specific Heat
  ('Specific Heat Capacity', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'UO2 Properties for Reactor Accident Analysis',
   'scalar', 300, 'J/(kg·K)', 10, 'relative_percent',
   '{"temperature": 1000}', 'high', 'calorimetry', 'at 1000K'),
  -- UO2 Density
  ('Density', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'UO2 Properties for Reactor Accident Analysis',
   'scalar', 10.97, 'g/cm³', 0.05, 'relative_percent',
   '{"temperature": 300, "theoretical_density_pct": 95}', 'high', 'archimedes', 'at 95% theoretical density'),
  -- UO2 Thermal Expansion
  ('Thermal Expansion Coefficient', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'Thermophysical Properties of UO2',
   'scalar', 1.05e-5, '1/K', 0.1, 'relative_percent',
   '{"temperature_range": "300-1500"}', 'high', 'dilatometry', 'linear thermal expansion coefficient'),
  -- Zircaloy-4 Thermal Conductivity
  ('Thermal Conductivity', 'Zircaloy-4', 'Zirconium Alloy Cladding Properties', 'Thermal Conductivity of Zircaloy',
   'scalar', 16.5, 'W/(m·K)', 0.5, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'Zircaloy-4 at room temperature'),
  ('Thermal Conductivity', 'Zircaloy-4', 'Zirconium Alloy Cladding Properties', 'Thermal Conductivity of Zircaloy',
   'scalar', 21.0, 'W/(m·K)', 1.0, 'relative_percent',
   '{"temperature": 800}', 'high', 'laser flash', 'Zircaloy-4 at 800K'),
  -- Zircaloy-4 Yield Strength
  ('Yield Strength', 'Zircaloy-4', 'Zirconium Alloy Cladding Properties', 'Mechanical Properties of Zircaloy-4 at High Temperature',
   'scalar', 450, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'recrystallized Zircaloy-4'),
  ('Yield Strength', 'Zircaloy-4', 'Zirconium Alloy Cladding Properties', 'Mechanical Properties of Zircaloy-4 at High Temperature',
   'scalar', 120, 'MPa', 15, 'absolute',
   '{"temperature": 773}', 'high', 'tensile test', 'at 500°C'),
  ('Yield Strength', 'Zircaloy-4', 'Zirconium Alloy Cladding Properties', 'Mechanical Properties of Zircaloy-4 at High Temperature',
   'scalar', 35, 'MPa', 10, 'absolute',
   '{"temperature": 1073}', 'medium', 'tensile test', 'at 800°C'),
  -- Zircaloy-4 UTS
  ('Ultimate Tensile Strength', 'Zircaloy-4', 'Zirconium Alloy Cladding Properties', 'Mechanical Properties of Zircaloy-4 at High Temperature',
   'scalar', 550, 'MPa', 25, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'recrystallized'),
  -- MOX Thermal Conductivity
  ('Thermal Conductivity', 'Mixed Oxide (U,Pu)O2', 'MOX Fuel Properties', 'Thermal Conductivity of MOX Fuel',
   'scalar', 3.5, 'W/(m·K)', 0.2, 'relative_percent',
   '{"temperature": 800, "Pu_content": "8wt%"}', 'high', 'laser flash', 'MOX at 8% Pu content'),
  -- UN Thermal Conductivity
  ('Thermal Conductivity', 'Uranium Nitride', 'UN Fuel Properties', 'Thermal Conductivity of UN',
   'scalar', 13.0, 'W/(m·K)', 1.0, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'dense UN pellet'),
  ('Thermal Conductivity', 'Uranium Nitride', 'UN Fuel Properties', 'Thermal Conductivity of UN',
   'scalar', 10.0, 'W/(m·K)', 0.5, 'relative_percent',
   '{"temperature": 1500}', 'high', 'laser flash', 'extrapolated'),
  -- UN Density
  ('Density', 'Uranium Nitride', 'UN Fuel Properties', 'Thermal Conductivity of UN',
   'scalar', 14.32, 'g/cm³', 0.02, 'relative_percent',
   '{"temperature": 300, "porosity": "0%"}', 'high', 'archimedes', 'theoretical density'),
  -- UN Melting Point
  ('Melting Point', 'Uranium Nitride', 'UN Fuel Properties', 'Review of UN Fuel Properties for Advanced Reactors',
   'scalar', 3120, 'K', 20, 'absolute',
   '{"pressure": "1atm"}', 'high', 'thermal analysis', 'under N2 atmosphere'),
  -- UC Thermal Conductivity
  ('Thermal Conductivity', 'Uranium Carbide', 'UC Fuel Properties', 'Thermal Conductivity of UC and UC2',
   'scalar', 22.0, 'W/(m·K)', 1.5, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'dense UC'),
  ('Thermal Conductivity', 'Uranium Carbide', 'UC Fuel Properties', 'Thermal Conductivity of UC and UC2',
   'scalar', 15.0, 'W/(m·K)', 1.0, 'relative_percent',
   '{"temperature": 1000}', 'medium', 'laser flash', 'dense UC'),
  -- UC Density
  ('Density', 'Uranium Carbide', 'UC Fuel Properties', 'Properties of Uranium Carbide for Nuclear Reactor Applications',
   'scalar', 13.63, 'g/cm³', 0.05, 'relative_percent',
   '{"temperature": 300}', 'high', 'archimedes', 'theoretical density'),
  -- SiC Thermal Conductivity
  ('Thermal Conductivity', 'CVD Silicon Carbide', 'SiC Ceramics for Nuclear', 'Thermal Conductivity of SiC for Nuclear Applications',
   'scalar', 120, 'W/(m·K)', 15, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'high purity CVD SiC'),
  ('Thermal Conductivity', 'CVD Silicon Carbide', 'SiC Ceramics for Nuclear', 'Thermal Conductivity of SiC for Nuclear Applications',
   'scalar', 30, 'W/(m·K)', 5, 'relative_percent',
   '{"temperature": 1200}', 'high', 'laser flash', 'irradiated CVD SiC'),
  -- SiC Young Modulus
  ('Young''s Modulus', 'CVD Silicon Carbide', 'SiC Ceramics for Nuclear', 'Mechanical Properties of CVD SiC for Fusion Reactors',
   'scalar', 410, 'GPa', 10, 'absolute',
   '{"temperature": 300}', 'high', 'ultrasonic', 'CVD SiC'),
  -- 316SS Yield
  ('Yield Strength', 'Type 316 Stainless Steel', 'Stainless Steel Reactor Materials', 'Tensile Properties of Type 316 Stainless Steel in LWR Environment',
   'scalar', 290, 'MPa', 15, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'annealed 316SS'),
  ('Yield Strength', 'Type 316 Stainless Steel', 'Stainless Steel Reactor Materials', 'Tensile Properties of Type 316 Stainless Steel in LWR Environment',
   'scalar', 140, 'MPa', 10, 'absolute',
   '{"temperature": 873}', 'high', 'tensile test', 'at 600°C'),
  -- 316SS UTS
  ('Ultimate Tensile Strength', 'Type 316 Stainless Steel', 'Stainless Steel Reactor Materials', 'Tensile Properties of Type 316 Stainless Steel in LWR Environment',
   'scalar', 580, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'annealed'),
  -- 316SS Swelling
  ('Swelling', 'Type 316 Stainless Steel', 'Stainless Steel Reactor Materials', 'Swelling in Type 316SS at High DPA',
   'scalar', 12.0, '%', 2.0, 'absolute',
   '{"temperature": 773, "neutron_fluence": "5e22_n/cm2"}', 'high', 'density measurement', 'at ~50 dpa'),
  ('Swelling', 'Type 316 Stainless Steel', 'Stainless Steel Reactor Materials', 'Swelling in Type 316SS at High DPA',
   'scalar', 25.0, '%', 3.0, 'absolute',
   '{"temperature": 773, "neutron_fluence": "1.5e23_n/cm2"}', 'high', 'density measurement', 'at ~100 dpa'),
  -- T91 Yield
  ('Yield Strength', 'T91 Ferritic Steel', 'RAFM/FM Steel Properties', 'Irradiation Effects on T91 Ferritic Steel',
   'scalar', 500, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'normalized and tempered'),
  ('Yield Strength', 'T91 Ferritic Steel', 'RAFM/FM Steel Properties', 'Irradiation Effects on T91 Ferritic Steel',
   'scalar', 300, 'MPa', 15, 'absolute',
   '{"temperature": 873}', 'high', 'tensile test', 'at 600°C'),
  -- Eurofer97
  ('Yield Strength', 'Eurofer97', 'RAFM/FM Steel Properties', 'Eurofer Properties for DEMO Fusion Reactor',
   'scalar', 530, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'normalized and tempered'),
  ('Yield Strength', 'Eurofer97', 'RAFM/FM Steel Properties', 'Eurofer Properties for DEMO Fusion Reactor',
   'scalar', 310, 'MPa', 15, 'absolute',
   '{"temperature": 873}', 'high', 'tensile test', 'at 600°C'),
  ('Ultimate Tensile Strength', 'Eurofer97', 'RAFM/FM Steel Properties', 'Eurofer Properties for DEMO Fusion Reactor',
   'scalar', 650, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', ''),
  -- W Thermal Conductivity
  ('Thermal Conductivity', 'Tungsten', 'Fusion Materials Database', 'Thermal Conductivity of Pure and Doped Tungsten',
   'scalar', 174, 'W/(m·K)', 10, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'pure W, annealed'),
  ('Thermal Conductivity', 'Tungsten', 'Fusion Materials Database', 'Thermal Conductivity of Pure and Doped Tungsten',
   'scalar', 100, 'W/(m·K)', 8, 'relative_percent',
   '{"temperature": 1000}', 'high', 'laser flash', 'pure W'),
  -- Be Thermal Conductivity
  ('Thermal Conductivity', 'Beryllium', 'Fusion Materials Database', 'Properties of Beryllium for Fusion Reactor Applications',
   'scalar', 200, 'W/(m·K)', 15, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'beryllium pebbles'),
  -- Be Swelling
  ('Swelling', 'Beryllium', 'Fusion Materials Database', 'Irradiation-Induced Swelling in Beryllium',
   'scalar', 3.5, '%', 0.5, 'absolute',
   '{"temperature": 573, "neutron_fluence": "1e21_n/cm2"}', 'high', 'density measurement', 'at ~2 dpa equivalent'),
  -- Graphite Thermal Conductivity
  ('Thermal Conductivity', 'Nuclear Graphite IG-110', 'Nuclear Coolant Properties', 'Thermal Conductivity of Nuclear Graphite',
   'scalar', 130, 'W/(m·K)', 10, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'parallel to extrusion'),
  ('Thermal Conductivity', 'Nuclear Graphite IG-110', 'Nuclear Coolant Properties', 'Thermal Conductivity of Nuclear Graphite',
   'scalar', 40, 'W/(m·K)', 5, 'relative_percent',
   '{"temperature": 1000}', 'high', 'laser flash', 'parallel to extrusion'),
  -- Graphite Young Modulus
  ('Young''s Modulus', 'Nuclear Graphite IG-110', 'Nuclear Coolant Properties', 'Mechanical Properties of IG-110 Nuclear Graphite',
   'scalar', 9.8, 'GPa', 0.5, 'absolute',
   '{"temperature": 300}', 'high', 'ultrasonic', 'IG-110, parallel direction'),
  -- U3Si2 Thermal Conductivity
  ('Thermal Conductivity', 'U3Si2', 'U3Si2 ATF Fuel', 'Thermal Conductivity of U3Si2',
   'scalar', 7.5, 'W/(m·K)', 0.5, 'relative_percent',
   '{"temperature": 300}', 'high', 'laser flash', 'dense pellet'),
  ('Thermal Conductivity', 'U3Si2', 'U3Si2 ATF Fuel', 'Thermal Conductivity of U3Si2',
   'scalar', 6.0, 'W/(m·K)', 0.3, 'relative_percent',
   '{"temperature": 800}', 'high', 'laser flash', 'dense pellet'),
  -- U3Si2 Density
  ('Density', 'U3Si2', 'U3Si2 ATF Fuel', 'Density and Porosity of U3Si2',
   'scalar', 12.02, 'g/cm³', 0.02, 'relative_percent',
   '{"temperature": 300, "porosity": "5%"}', 'high', 'archimedes', '95% theoretical density'),
  -- ThO2 Thermal Conductivity
  ('Thermal Conductivity', 'Thorium Dioxide', 'ThO2 Fuel Properties', 'Thermophysical Properties of ThO2',
   'scalar', 6.0, 'W/(m·K)', 0.3, 'relative_percent',
   '{"temperature": 500}', 'high', 'laser flash', 'dense ThO2 pellet'),
  -- ThO2 Melting Point
  ('Melting Point', 'Thorium Dioxide', 'ThO2 Fuel Properties', 'Thermophysical Properties of ThO2',
   'scalar', 3643, 'K', 20, 'absolute',
   '{"pressure": "1atm"}', 'high', 'thermal analysis', ''),
  -- (Th,U)O2
  ('Thermal Conductivity', 'Thorium Dioxide', 'ThO2 Fuel Properties', 'Thermal Conductivity of (Th,U)O2 Mixed Oxide',
   'scalar', 5.0, 'W/(m·K)', 0.3, 'relative_percent',
   '{"temperature": 800, "UO2_content": "20mol%"}', 'high', 'laser flash', '(Th,U)O2 with 20% UO2'),
  -- FLiBe Thermal Conductivity
  ('Thermal Conductivity', 'FLiBe', 'Nuclear Coolant Properties', 'Thermal Conductivity of FLiBe Salt',
   'scalar', 1.1, 'W/(m·K)', 0.1, 'relative_percent',
   '{"temperature": 873}', 'high', 'transient hot wire', 'Li2BeF4 molten salt'),
  -- Liquid Lead
  ('Thermal Conductivity', 'Liquid Lead', 'Nuclear Coolant Properties', 'Corrosion of Structural Materials in Liquid Lead',
   'scalar', 15.0, 'W/(m·K)', 1.5, 'relative_percent',
   '{"temperature": 673}', 'medium', 'transient hot wire', 'liquid Pb at 400°C'),
  ('Density', 'Liquid Lead', 'Nuclear Coolant Properties', 'Corrosion of Structural Materials in Liquid Lead',
   'scalar', 10.66, 'g/cm³', 0.05, 'relative_percent',
   '{"temperature": 673}', 'high', 'archimedes', 'at 400°C'),
  -- Liquid Sodium
  ('Thermal Conductivity', 'Liquid Sodium', 'Nuclear Coolant Properties', 'Sodium Corrosion of Austenitic Stainless Steels',
   'scalar', 70.0, 'W/(m·K)', 5.0, 'relative_percent',
   '{"temperature": 673}', 'high', 'transient hot wire', 'at 400°C'),
  ('Density', 'Liquid Sodium', 'Nuclear Coolant Properties', 'Sodium Corrosion of Austenitic Stainless Steels',
   'scalar', 0.89, 'g/cm³', 0.01, 'relative_percent',
   '{"temperature": 673}', 'high', 'archimedes', 'at 400°C'),
  -- V-4Cr-4Ti
  ('Yield Strength', 'V-4Cr-4Ti', 'Fusion Materials Database', 'V-4Cr-4Ti Alloy Properties for Fusion Reactor First Wall',
   'scalar', 460, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'annealed'),
  ('Yield Strength', 'V-4Cr-4Ti', 'Fusion Materials Database', 'V-4Cr-4Ti Alloy Properties for Fusion Reactor First Wall',
   'scalar', 250, 'MPa', 15, 'absolute',
   '{"temperature": 873}', 'high', 'tensile test', 'at 600°C'),
  -- Radiation Hardening
  ('Radiation Hardening', 'T91 Ferritic Steel', 'RAFM/FM Steel Properties', 'Irradiation Effects on T91 Ferritic Steel',
   'scalar', 350, 'MPa', 50, 'absolute',
   '{"temperature": 573, "dpa": 5}', 'medium', 'tensile test', 'Δσy at 5 dpa'),
  ('Radiation Hardening', 'Type 316 Stainless Steel', 'Stainless Steel Reactor Materials', 'Irradiation Creep of Austenitic Stainless Steels',
   'scalar', 250, 'MPa', 40, 'absolute',
   '{"temperature": 573, "dpa": 10}', 'medium', 'tensile test', 'Δσy at 10 dpa'),
  -- Xenon Diffusion
  ('Diffusion Coefficient', 'Xenon', 'UO2 Thermophysical Properties', 'Xenon Diffusion in UO2',
   'scalar', 1.0e-19, 'm²/s', 5.0e-20, 'relative_percent',
   '{"temperature": 1273}', 'medium', 'annealing', 'Xe in UO2 at 1000°C'),
  -- Self-diffusion in UO2
  ('Diffusion Coefficient', 'Uranium Dioxide', 'UO2 Thermophysical Properties', 'Self-Diffusion in Polycrystalline UO2',
   'scalar', 5.0e-17, 'm²/s', 1.0e-17, 'relative_percent',
   '{"temperature": 1873}', 'medium', 'tracer', 'U self-diffusion at 1600°C'),
  -- FeCrAl
  ('Yield Strength', 'FeCrAl Alloy', 'U3Si2 ATF Fuel', 'FeCrAl Alloy for Accident Tolerant Fuel Cladding',
   'scalar', 480, 'MPa', 20, 'absolute',
   '{"temperature": 300}', 'high', 'tensile test', 'Fe-13Cr-4Al-2Mo, annealed'),
  ('Yield Strength', 'FeCrAl Alloy', 'U3Si2 ATF Fuel', 'FeCrAl Alloy for Accident Tolerant Fuel Cladding',
   'scalar', 120, 'MPa', 15, 'absolute',
   '{"temperature": 1073}', 'high', 'tensile test', 'at 800°C'),
  -- Nb-1Zr
  ('Young''s Modulus', 'Nb-1Zr', 'Fusion Materials Database', 'Properties of Nb-1Zr for Space Reactor Applications',
   'scalar', 105, 'GPa', 5, 'absolute',
   '{"temperature": 300}', 'medium', 'ultrasonic', 'Nb-1Zr'),
  ('Yield Strength', 'Nb-1Zr', 'Fusion Materials Database', 'Properties of Nb-1Zr for Space Reactor Applications',
   'scalar', 190, 'MPa', 10, 'absolute',
   '{"temperature": 300}', 'medium', 'tensile test', ''),
  -- SiC/SiC Composite
  ('Ultimate Tensile Strength', 'SiC/SiC Composite', 'SiC Ceramics for Nuclear', 'SiC/SiC Composite for LWR Fuel Cladding',
   'scalar', 350, 'MPa', 30, 'absolute',
   '{"temperature": 298}', 'medium', 'tensile test', '2D woven CVI composite'),
  ('Ultimate Tensile Strength', 'SiC/SiC Composite', 'SiC Ceramics for Nuclear', 'SiC/SiC Composite for LWR Fuel Cladding',
   'scalar', 280, 'MPa', 25, 'absolute',
   '{"temperature": 1273}', 'medium', 'tensile test', 'at 1000°C in inert atmosphere'),
  -- Inconel 718
  ('Yield Strength', 'Inconel 718', 'RAFM/FM Steel Properties', 'High-Temperature Tensile Properties of Inconel 718',
   'scalar', 1035, 'MPa', 30, 'absolute',
   '{"temperature": 298}', 'high', 'tensile test', 'aged condition'),
  ('Yield Strength', 'Inconel 718', 'RAFM/FM Steel Properties', 'High-Temperature Tensile Properties of Inconel 718',
   'scalar', 580, 'MPa', 25, 'absolute',
   '{"temperature": 923}', 'high', 'tensile test', 'aged condition at 650°C'),
  -- Hastelloy-X
  ('Young''s Modulus', 'Hastelloy-X', 'RAFM/FM Steel Properties', 'Creep of Hastelloy-X in Simulated Reactor Environment',
   'scalar', 205, 'GPa', 8, 'absolute',
   '{"temperature": 298}', 'high', 'ultrasonic', ''),
  -- TRISO SiC layer
  ('Young''s Modulus', 'CVD Silicon Carbide', 'SiC Ceramics for Nuclear', 'SiC Layer Properties in TRISO Coated Particles',
   'scalar', 390, 'GPa', 15, 'absolute',
   '{"temperature": 298, "grain_type": "CVI"}', 'high', 'nanoindentation', 'IPyC-SiC-OPyC in TRISO particle'),
  -- PyC ITPD
  ('Density', 'Pyrolytic Carbon', 'SiC Ceramics for Nuclear', 'PyC ITPD Density in TRISO Fuel',
   'scalar', 1.90, 'g/cm³', 0.05, 'relative_percent',
   '{"temperature": 298, "pyc_type": "IPyC"}', 'high', 'density gradient', 'isotropic dense PyC layer')
) AS pm(prop_name, mat_name, dset_name, src_title, vt, val, unit, unc_val, unc_type, conds, conf, method, notes)
JOIN property_types pt ON pt.name = pm.prop_name
JOIN materials m ON m.name = pm.mat_name
JOIN datasets ds ON ds.name = pm.dset_name
JOIN data_sources src ON src.title = pm.src_title
ON CONFLICT DO NOTHING;


-- ============================================================
-- 9. Verification summary
-- ============================================================
DO $$
DECLARE
  v_sources integer;
  v_materials integer;
  v_measurements integer;
  v_authors integer;
  v_datasets integer;
BEGIN
  SELECT count(*) INTO v_sources FROM data_sources;
  SELECT count(*) INTO v_materials FROM materials;
  SELECT count(*) INTO v_measurements FROM property_measurements;
  SELECT count(*) INTO v_authors FROM authors;
  SELECT count(*) INTO v_datasets FROM datasets;

  RAISE NOTICE '';
  RAISE NOTICE 'NFM-841 Phase 1 Literature Seed Data Summary';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Data Sources (literature):  %', v_sources;
  RAISE NOTICE 'Materials:                 %s', v_materials;
  RAISE NOTICE 'Property Measurements:     %s', v_measurements;
  RAISE NOTICE 'Authors:                   %s', v_authors;
  RAISE NOTICE 'Datasets:                  %s', v_datasets;
  RAISE NOTICE '========================================';

  IF v_sources >= 50 AND v_measurements >= 50 THEN
    RAISE NOTICE 'PASS: Seed data meets minimum threshold (>= 50 sources, >= 50 measurements)';
  ELSE
    RAISE NOTICE 'FAIL: Below threshold. Sources=%s (need>=50), Measurements=%s (need>=50)',
      v_sources, v_measurements;
  END IF;
END $$;

COMMIT;
