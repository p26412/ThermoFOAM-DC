/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | ThermoFOAM-DC v0.1
    \\  /    A nd           | Publication-track data-center metrics
     \\/     M anipulation  |
-------------------------------------------------------------------------------
Application
    dcMetricsPlus

Description
    Computes robust data-center cooling metrics for ThermoFOAM-DC v0.1.

    Compared with the earlier dcMetrics utility, this version adds:
      - T95 room temperature
      - T95 rack-inlet temperature
      - rack-inlet volume fraction above a rack-risk threshold
      - room volume fraction above a separate room-hotspot threshold
      - area-averaged return temperature
      - outflow-weighted return temperature using U dot Sf on returnOutlet

    Run examples:
        dcMetricsPlus -latestTime
        dcMetricsPlus -time 8000
        dcMetricsPlus -time '5000:8000'

    Dictionary:
        system/dcMetricsDict
\*---------------------------------------------------------------------------*/

#include "argList.H"
#include "timeSelector.H"
#include "fvMesh.H"
#include "volFields.H"
#include "surfaceFields.H"
#include "IOdictionary.H"
#include "OFstream.H"
#include "OSspecific.H"

#include <algorithm>
#include <vector>
#include <utility>
#include <limits>

using namespace Foam;

static bool insideBox(const vector& c, const vector& bMin, const vector& bMax)
{
    return
    (
        c.x() >= bMin.x() && c.x() <= bMax.x()
     && c.y() >= bMin.y() && c.y() <= bMax.y()
     && c.z() >= bMin.z() && c.z() <= bMax.z()
    );
}

static label findPatchIDCompat(const fvMesh& mesh, const word& patchName)
{
    const fvBoundaryMesh& patches = mesh.boundary();

    forAll(patches, patchI)
    {
        if (patches[patchI].name() == patchName)
        {
            return patchI;
        }
    }

    return -1;
}

static scalar patchAreaAverage(const volScalarField& field, const word& patchName)
{
    const fvMesh& mesh = field.mesh();
    const label patchID = findPatchIDCompat(mesh, patchName);

    if (patchID < 0)
    {
        FatalErrorInFunction
            << "Cannot find patch " << patchName << nl
            << "Check system/dcMetricsDict and constant/polyMesh/boundary."
            << exit(FatalError);
    }

    const auto& values = field.boundaryField()[patchID];
    const auto& areas = mesh.magSf().boundaryField()[patchID];

    scalar sumArea = 0.0;
    scalar sumValueArea = 0.0;

    forAll(values, faceI)
    {
        sumArea += areas[faceI];
        sumValueArea += values[faceI]*areas[faceI];
    }

    if (sumArea <= vSmall)
    {
        return GREAT;
    }

    return sumValueArea/sumArea;
}

static scalar outflowWeightedPatchAverage
(
    const volScalarField& T,
    const volVectorField& U,
    const word& patchName,
    scalar& outflowFlux
)
{
    const fvMesh& mesh = T.mesh();
    const label patchID = findPatchIDCompat(mesh, patchName);

    if (patchID < 0)
    {
        FatalErrorInFunction
            << "Cannot find patch " << patchName << nl
            << "Check system/dcMetricsDict and constant/polyMesh/boundary."
            << exit(FatalError);
    }

    const auto& Tp = T.boundaryField()[patchID];
    const auto& Up = U.boundaryField()[patchID];
    const auto& Sf = mesh.Sf().boundaryField()[patchID];

    outflowFlux = 0.0;
    scalar weightedT = 0.0;

    forAll(Tp, faceI)
    {
        const scalar phi = (Up[faceI] & Sf[faceI]);

        // Positive flux means out of the domain for the patch normal convention.
        if (phi > 0)
        {
            outflowFlux += phi;
            weightedT += phi*Tp[faceI];
        }
    }

    if (outflowFlux <= vSmall)
    {
        return GREAT;
    }

    return weightedT/outflowFlux;
}

static bool fieldHeaderOk(const word& fieldName, const Time& runTime, const fvMesh& mesh)
{
    IOobject header
    (
        fieldName,
        runTime.name(),
        mesh,
        IOobject::READ_IF_PRESENT,
        IOobject::NO_WRITE,
        false
    );

    return header.headerOk();
}

static scalar weightedPercentile
(
    std::vector<std::pair<scalar, scalar> >& valuesAndWeights,
    const scalar percentile
)
{
    if (valuesAndWeights.empty())
    {
        return GREAT;
    }

    std::sort
    (
        valuesAndWeights.begin(),
        valuesAndWeights.end(),
        [](const std::pair<scalar, scalar>& a, const std::pair<scalar, scalar>& b)
        {
            return a.first < b.first;
        }
    );

    scalar totalWeight = 0.0;
    for (const auto& vw : valuesAndWeights)
    {
        totalWeight += vw.second;
    }

    if (totalWeight <= vSmall)
    {
        return valuesAndWeights.back().first;
    }

    const scalar target = Foam::max(scalar(0), Foam::min(scalar(1), percentile))*totalWeight;
    scalar cumulative = 0.0;

    for (const auto& vw : valuesAndWeights)
    {
        cumulative += vw.second;
        if (cumulative >= target)
        {
            return vw.first;
        }
    }

    return valuesAndWeights.back().first;
}

int main(int argc, char *argv[])
{
    timeSelector::addOptions();

    #include "setRootCase.H"
    #include "createTime.H"

    instantList timeDirs = timeSelector::select0(runTime, args);

    #include "createMesh.H"

    IOdictionary dict
    (
        IOobject
        (
            "dcMetricsDict",
            runTime.system(),
            mesh,
            IOobject::MUST_READ,
            IOobject::NO_WRITE
        )
    );

    const word temperatureField(dict.lookupOrDefault<word>("temperatureField", "T"));
    word pressureField(dict.lookupOrDefault<word>("pressureField", "p_rgh"));
    const word velocityField(dict.lookupOrDefault<word>("velocityField", "U"));

    const word supplyPatch(dict.lookupOrDefault<word>("supplyPatch", "supplyTiles"));
    const word returnPatch(dict.lookupOrDefault<word>("returnPatch", "returnOutlet"));

    const scalar rackInletRiskThreshold
    (
        dict.lookupOrDefault<scalar>("rackInletRiskThreshold", 305.0)
    );

    const scalar roomHotspotThreshold
    (
        dict.lookupOrDefault<scalar>("roomHotspotThreshold", 315.0)
    );

    const List<vector> rackInletBoxMin(dict.lookup("rackInletBoxMin"));
    const List<vector> rackInletBoxMax(dict.lookup("rackInletBoxMax"));

    if (rackInletBoxMin.size() != rackInletBoxMax.size())
    {
        FatalErrorInFunction
            << "rackInletBoxMin and rackInletBoxMax must have the same size."
            << exit(FatalError);
    }

    forAll(timeDirs, timeI)
    {
        runTime.setTime(timeDirs[timeI], timeI);
        mesh.readUpdate();

        Info<< nl << "Time = " << runTime.userTimeName() << nl << endl;
        Info<< "Reading field " << temperatureField << nl << endl;

        volScalarField T
        (
            IOobject
            (
                temperatureField,
                runTime.name(),
                mesh,
                IOobject::MUST_READ,
                IOobject::NO_WRITE
            ),
            mesh
        );

        Info<< "Reading velocity field " << velocityField << nl << endl;

        volVectorField U
        (
            IOobject
            (
                velocityField,
                runTime.name(),
                mesh,
                IOobject::MUST_READ,
                IOobject::NO_WRITE
            ),
            mesh
        );

        if (!fieldHeaderOk(pressureField, runTime, mesh))
        {
            if (pressureField != "p_rgh" && fieldHeaderOk("p_rgh", runTime, mesh))
            {
                WarningInFunction
                    << "Pressure field " << pressureField
                    << " not found at time " << runTime.name()
                    << ". Using p_rgh instead." << nl << endl;

                pressureField = "p_rgh";
            }
            else if (pressureField != "p" && fieldHeaderOk("p", runTime, mesh))
            {
                WarningInFunction
                    << "Pressure field " << pressureField
                    << " not found at time " << runTime.name()
                    << ". Using p instead." << nl << endl;

                pressureField = "p";
            }
            else
            {
                FatalErrorInFunction
                    << "Cannot find pressure field " << pressureField
                    << ", p, or p_rgh at time " << runTime.name() << nl
                    << "Set pressureField correctly in system/dcMetricsDict."
                    << exit(FatalError);
            }
        }

        Info<< "Reading pressure field " << pressureField << nl << endl;

        volScalarField p
        (
            IOobject
            (
                pressureField,
                runTime.name(),
                mesh,
                IOobject::MUST_READ,
                IOobject::NO_WRITE
            ),
            mesh
        );

        const scalarField& Ti = T.primitiveField();
        const auto& V = mesh.V();
        const auto& C = mesh.C();

        scalar totalVolume = 0.0;
        scalar TsumVolume = 0.0;
        scalar TmaxRoom = -great;
        scalar roomHotspotVolume = 0.0;

        scalar rackInletVolume = 0.0;
        scalar rackInletTsumVolume = 0.0;
        scalar TmaxRackInlet = -great;
        scalar rackInletHotspotVolume = 0.0;
        label nRackInletCells = 0;

        std::vector<std::pair<scalar, scalar> > roomTV;
        std::vector<std::pair<scalar, scalar> > rackInletTV;
        roomTV.reserve(Ti.size());

        forAll(Ti, cellI)
        {
            const scalar vol = V[cellI];
            const scalar t = Ti[cellI];

            totalVolume += vol;
            TsumVolume += t*vol;
            roomTV.push_back(std::make_pair(t, vol));

            if (t > TmaxRoom)
            {
                TmaxRoom = t;
            }

            if (t > roomHotspotThreshold)
            {
                roomHotspotVolume += vol;
            }

            bool inRackInlet = false;
            forAll(rackInletBoxMin, boxI)
            {
                if (insideBox(C[cellI], rackInletBoxMin[boxI], rackInletBoxMax[boxI]))
                {
                    inRackInlet = true;
                    break;
                }
            }

            if (inRackInlet)
            {
                nRackInletCells++;
                rackInletVolume += vol;
                rackInletTsumVolume += t*vol;
                rackInletTV.push_back(std::make_pair(t, vol));

                if (t > TmaxRackInlet)
                {
                    TmaxRackInlet = t;
                }

                if (t > rackInletRiskThreshold)
                {
                    rackInletHotspotVolume += vol;
                }
            }
        }

        if (totalVolume <= vSmall)
        {
            FatalErrorInFunction
                << "Total mesh volume is zero."
                << exit(FatalError);
        }

        if (nRackInletCells == 0)
        {
            WarningInFunction
                << "No cells found inside rack inlet monitor boxes." << nl
                << "Check rackInletBoxMin/rackInletBoxMax in system/dcMetricsDict."
                << nl << endl;
        }

        const scalar TavgRoom = TsumVolume/totalVolume;
        const scalar T95Room = weightedPercentile(roomTV, 0.95);
        const scalar roomHotspotVolumeFraction = roomHotspotVolume/totalVolume;

        const scalar TavgRackInlet =
            rackInletVolume > vSmall ? rackInletTsumVolume/rackInletVolume : GREAT;

        const scalar T95RackInlet = weightedPercentile(rackInletTV, 0.95);

        const scalar rackInletHotspotFraction =
            rackInletVolume > vSmall ? rackInletHotspotVolume/rackInletVolume : GREAT;

        const scalar returnOutletTareaAvg = patchAreaAverage(T, returnPatch);
        scalar returnOutletOutflowFlux = 0.0;
        const scalar returnOutletTmassFlowAvg =
            outflowWeightedPatchAverage(T, U, returnPatch, returnOutletOutflowFlux);

        const scalar supplyPressureAvg = patchAreaAverage(p, supplyPatch);
        const scalar returnPressureAvg = patchAreaAverage(p, returnPatch);
        const scalar deltaP = supplyPressureAvg - returnPressureAvg;

        const label nCells = mesh.nCells();
        const scalar hEff = Foam::pow(totalVolume/scalar(nCells), 1.0/3.0);

        fileName outDir = runTime.path()/"postProcessing"/"dcMetricsPlus"/runTime.name();
        mkDir(outDir);

        fileName outFile = outDir/"metrics.csv";
        OFstream os(outFile);
        os.precision(12);

        os  << "casePath,time,nCells,totalVolume,hEff,"
            << "TmaxRoom,TavgRoom,T95Room,roomHotspotThreshold,roomHotspotVolume,roomHotspotVolumeFraction,"
            << "TmaxRackInlet,TavgRackInlet,T95RackInlet,rackInletRiskThreshold,rackInletHotspotVolume,rackInletHotspotFraction,nRackInletCells,"
            << "returnOutletTareaAvg,returnOutletTmassFlowAvg,returnOutletOutflowFlux,"
            << "pressureField,supplyPressureAvg,returnPressureAvg,deltaP_supply_minus_return"
            << nl;

        os  << runTime.path() << ','
            << runTime.name() << ','
            << nCells << ','
            << totalVolume << ','
            << hEff << ','
            << TmaxRoom << ','
            << TavgRoom << ','
            << T95Room << ','
            << roomHotspotThreshold << ','
            << roomHotspotVolume << ','
            << roomHotspotVolumeFraction << ','
            << TmaxRackInlet << ','
            << TavgRackInlet << ','
            << T95RackInlet << ','
            << rackInletRiskThreshold << ','
            << rackInletHotspotVolume << ','
            << rackInletHotspotFraction << ','
            << nRackInletCells << ','
            << returnOutletTareaAvg << ','
            << returnOutletTmassFlowAvg << ','
            << returnOutletOutflowFlux << ','
            << pressureField << ','
            << supplyPressureAvg << ','
            << returnPressureAvg << ','
            << deltaP
            << nl;

        Info<< "Wrote " << outFile << nl << endl;
        Info<< "TavgRackInlet              = " << TavgRackInlet << nl;
        Info<< "T95RackInlet               = " << T95RackInlet << nl;
        Info<< "TmaxRackInlet              = " << TmaxRackInlet << nl;
        Info<< "TavgRoom                   = " << TavgRoom << nl;
        Info<< "T95Room                    = " << T95Room << nl;
        Info<< "TmaxRoom                   = " << TmaxRoom << nl;
        Info<< "Return T area average      = " << returnOutletTareaAvg << nl;
        Info<< "Return T outflow-weighted  = " << returnOutletTmassFlowAvg << nl;
        Info<< "Room hotspot fraction      = " << roomHotspotVolumeFraction << nl;
        Info<< "Rack inlet risk fraction   = " << rackInletHotspotFraction << nl;
        Info<< "Delta p supply-return      = " << deltaP << nl << endl;
    }

    Info<< "End\n" << endl;
    return 0;
}

// ************************************************************************* //
