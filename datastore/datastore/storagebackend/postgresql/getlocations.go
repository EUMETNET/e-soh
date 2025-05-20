package postgresql

import (
	"datastore/datastore"

	_ "github.com/lib/pq"
	"google.golang.org/grpc/codes"
)

// GetLocations ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) GetLocations(_ *datastore.GetLocationsRequest) (
	*datastore.GetLocationsResponse, codes.Code, string,
) {
	// TODO ...

	// for now:
	locs := []*datastore.LocMetadata{}
	return &datastore.GetLocationsResponse{
		Locations: locs,
	}, codes.OK, ""
}
