package storagebackend

import (
	"datastore/common"
	datastore "datastore/datastore"

	"google.golang.org/grpc/codes"
)

// StorageBackend is the interface for an observation storage backend.
type StorageBackend interface {

	// Description returns the description of the backend.
	Description() string

	// PutObservations inserts observations in the storage.
	//
	// Returns (codes.OK, ...) upon success, otherwise (error code, reason).
	PutObservations(*datastore.PutObsRequest) (codes.Code, string)

	// GetObservations retrieves observations from the storage.
	//
	// Returns (observations, codes.OK, ...) upon success, otherwise (..., error code, reason).
	GetObservations(*datastore.GetObsRequest, common.TemporalSpec) (
		*datastore.GetObsResponse, codes.Code, string)

	// GetTSAttrGroups retrieves, for the non-default attributes in the input, the unique
	// combinations of attribute values currently represented in the storage.
	//
	// Returns (combos, codes.OK, ...) upon success, otherwise (..., error code, reason).
	GetTSAttrGroups(*datastore.GetTSAGRequest) (*datastore.GetTSAGResponse, codes.Code, string)

	// GetExtents gets the time- and geo extents of all currently stored observations.
	//
	// Returns (extents, codes.OK, ...) upon success, otherwise (..., error code, reason).
	GetExtents(*datastore.GetExtentsRequest) (*datastore.GetExtentsResponse, codes.Code, string)

	// GetLocations gets the locations of the most recent observation of the distinct platforms
	// currently represented in the storage.
	GetLocations(*datastore.GetLocationsRequest) (
		*datastore.GetLocationsResponse, codes.Code, string)
}
